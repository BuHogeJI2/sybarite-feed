import argparse
import json
import logging
import os
import sys
from dataclasses import asdict
from functools import partial
from pathlib import Path

from sybarite_feed.channel import list_videos
from sybarite_feed.config import load_config
from sybarite_feed.cookies import InvalidCookieFile, cookie_values, mask_commands
from sybarite_feed.download import download_audio
from sybarite_feed.run import run_update
from sybarite_feed.storage import ConflictError, R2Storage


def main() -> None:
    parser = argparse.ArgumentParser(prog="sybarite_feed")
    commands = parser.add_subparsers(dest="command", required=True)
    download = commands.add_parser("download", help="download the audio of one video")
    download.add_argument("--id", required=True, help="YouTube video ID")
    download.add_argument("--out", type=Path, default=Path("tmp"), help="output directory")
    run = commands.add_parser("run", help="download new videos, upload them and publish the feed")
    run.add_argument("--limit", type=int, help="max videos to download (default: channel.batch_size)")
    run.add_argument("--work-dir", type=Path, default=Path("tmp"), help="directory for downloads in progress")
    check = commands.add_parser("check-cookies", help="check a cookies.txt file without printing its content")
    check.add_argument("path", type=Path)
    check.add_argument("--mask", action="store_true", help="print GitHub Actions commands that hide the values")
    args = parser.parse_args()

    if args.command == "check-cookies":
        values = _checked_cookie_values(args.path)
        if args.mask:
            for command in mask_commands(values):
                print(command)
        print(f"{len(values)} cookies are valid")
        return

    config = load_config()
    cookie_file = os.environ.get("YT_COOKIES_FILE")
    if cookie_file:
        _checked_cookie_values(cookie_file)
    if args.command == "download":
        args.out.mkdir(parents=True, exist_ok=True)
        result = download_audio(args.id, args.out, config.channel.audio_format, cookie_file)
        print(json.dumps({**asdict(result.episode), "path": str(result.path)}, default=str, ensure_ascii=False, indent=2))
    elif args.command == "run":
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
        args.work_dir.mkdir(parents=True, exist_ok=True)
        try:
            result = run_update(
                R2Storage.from_env(),
                config,
                limit=config.channel.batch_size if args.limit is None else args.limit,
                list_videos=list_videos,
                download=partial(
                    download_audio, out_dir=args.work_dir, audio_format=config.channel.audio_format, cookie_file=cookie_file
                ),
            )
        except ConflictError:
            logging.error("state.json was changed by another run; stopping")
            sys.exit(1)
        logging.info("done: %d added, %d failed", len(result.added), len(result.failed))
        sys.exit(0 if result.ok else 1)


def _checked_cookie_values(path: str | Path) -> list[str]:
    try:
        return cookie_values(path)
    except InvalidCookieFile as error:
        sys.exit(f"invalid cookie file: {error}")


if __name__ == "__main__":
    main()
