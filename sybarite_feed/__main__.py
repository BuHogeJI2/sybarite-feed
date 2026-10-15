import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from sybarite_feed.config import load_config
from sybarite_feed.download import download_audio


def main() -> None:
    parser = argparse.ArgumentParser(prog="sybarite_feed")
    commands = parser.add_subparsers(dest="command", required=True)
    download = commands.add_parser("download", help="download the audio of one video")
    download.add_argument("--id", required=True, help="YouTube video ID")
    download.add_argument("--out", type=Path, default=Path("tmp"), help="output directory")
    args = parser.parse_args()

    config = load_config()
    if args.command == "download":
        args.out.mkdir(parents=True, exist_ok=True)
        result = download_audio(args.id, args.out, config.channel.audio_format, os.environ.get("YT_COOKIES_FILE"))
        print(json.dumps({**asdict(result.episode), "path": str(result.path)}, default=str, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
