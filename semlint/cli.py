from __future__ import annotations

import argparse
import sys

from semlint.engine import audit_file
from semlint.report import write_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="semlint", description="audit semantic-layer metric definitions"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit", help="audit a metrics definition file")
    audit.add_argument("file", help="path to a metrics YAML file")
    audit.add_argument(
        "--report", default=None, help="markdown report path (JSON written alongside)"
    )
    args = parser.parse_args(argv)

    if args.command == "audit":
        result = audit_file(args.file)
        c = {"pass": 0, "warn": 0, "fail": 0}
        for f in result.findings:
            c[f.severity.value] += 1
        print(f"Semantic Trust Score: {result.score}/100")
        print(f"findings: {c['fail']} fail, {c['warn']} warn, {c['pass']} pass")
        if args.report:
            written = write_report(result, args.report)
            print(f"markdown: {written['markdown']}")
            print(f"json: {written['json']}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
