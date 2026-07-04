from __future__ import annotations

import argparse
import json
import logging
import sys

from watcher.config import load_settings
from watcher.service import WatchService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the JAL/ANA domestic sale watcher once."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run checks without sending LINE notifications.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the result as JSON.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Set the logging level.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    try:
        settings = load_settings()
        service = WatchService.from_settings(settings)
        result = service.run(dry_run=args.dry_run)
    except Exception as exc:
        logging.exception("Watcher execution failed: %s", exc)
        if args.json:
            print(
                json.dumps(
                    {"ok": False, "error": str(exc)},
                    ensure_ascii=False,
                )
            )
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        logging.info("Watcher finished: ok=%s dry_run=%s", result["ok"], args.dry_run)
        for item in result["results"]:
            logging.info(
                "airline=%s changed=%s notified=%s recovered=%s error=%s",
                item["airline"],
                item["changed"],
                item["notified"],
                item["recovered"],
                item["error"],
            )
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
