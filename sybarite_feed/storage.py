import hashlib
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


class ConflictError(Exception):
    pass


@dataclass(frozen=True)
class StoredObject:
    data: bytes
    etag: str


class Storage(Protocol):
    def get(self, key: str) -> StoredObject | None: ...

    def put(
        self,
        key: str,
        data: bytes,
        content_type: str,
        *,
        cache_control: str | None = None,
        if_match: str | None = None,
        if_none_match: bool = False,
    ) -> str: ...

    def upload_file(self, key: str, path: Path, content_type: str, *, cache_control: str | None = None) -> None: ...


class LocalStorage:
    def __init__(self, root: Path):
        self.root = root

    def get(self, key: str) -> StoredObject | None:
        path = self.root / key
        if not path.exists():
            return None
        data = path.read_bytes()
        return StoredObject(data=data, etag=_etag(data))

    def put(
        self,
        key: str,
        data: bytes,
        content_type: str,
        *,
        cache_control: str | None = None,
        if_match: str | None = None,
        if_none_match: bool = False,
    ) -> str:
        current = self.get(key)
        if if_none_match and current is not None:
            raise ConflictError(key)
        if if_match is not None and (current is None or current.etag != if_match):
            raise ConflictError(key)
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return _etag(data)

    def upload_file(self, key: str, path: Path, content_type: str, *, cache_control: str | None = None) -> None:
        target = self.root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


class R2Storage:
    def __init__(self, account_id: str, access_key_id: str, secret_access_key: str, bucket: str):
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name="auto",
            # boto3 1.36+ adds checksum headers by default, which Cloudflare advises turning off for R2
            config=Config(request_checksum_calculation="when_required", response_checksum_validation="when_required"),
        )

    @classmethod
    def from_env(cls) -> "R2Storage":
        return cls(
            account_id=os.environ["R2_ACCOUNT_ID"],
            access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
            bucket=os.environ["R2_BUCKET"],
        )

    def get(self, key: str) -> StoredObject | None:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as error:
            if error.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise
        return StoredObject(data=response["Body"].read(), etag=response["ETag"])

    def put(
        self,
        key: str,
        data: bytes,
        content_type: str,
        *,
        cache_control: str | None = None,
        if_match: str | None = None,
        if_none_match: bool = False,
    ) -> str:
        arguments = {"Bucket": self.bucket, "Key": key, "Body": data, "ContentType": content_type}
        if cache_control:
            arguments["CacheControl"] = cache_control
        if if_match is not None:
            arguments["IfMatch"] = if_match
        if if_none_match:
            arguments["IfNoneMatch"] = "*"
        try:
            return self.client.put_object(**arguments)["ETag"]
        except ClientError as error:
            if error.response["Error"]["Code"] == "PreconditionFailed":
                raise ConflictError(key) from error
            raise

    def upload_file(self, key: str, path: Path, content_type: str, *, cache_control: str | None = None) -> None:
        extra = {"ContentType": content_type}
        if cache_control:
            extra["CacheControl"] = cache_control
        self.client.upload_file(str(path), self.bucket, key, ExtraArgs=extra)


def _etag(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
