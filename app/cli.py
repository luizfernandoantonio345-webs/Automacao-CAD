from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import json
import sys

from .runtime import run_job, write_sample_spec
from .spec import load_spec, parse_spec, sample_spec


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(prog="app", description="CAD automation entrypoint")
    parser.add_argument("--spec", type=Path, help="Path to the job spec JSON")
    parser.add_argument("--output", type=Path, help="Override the spec output directory")
    parser.add_argument("--write-sample-spec", type=Path, help="Write a starter spec JSON and exit")
    parser.add_argument("--print-sample-spec", action="store_true", help="Print a sample spec to stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.write_sample_spec:
        write_sample_spec(args.write_sample_spec)
        return 0

    if args.print_sample_spec:
        print(json.dumps(sample_spec(), indent=2, ensure_ascii=True))
        return 0

    if not args.spec:
        build_parser().error("the following arguments are required: --spec")
        return 2

    spec = load_spec(args.spec)
    if args.output:
        spec = parse_spec(
            {
                "job_name": spec.job_name,
                "output_dir": str(args.output),
                "drawing": {
                    "name": spec.drawing.name,
                    "units": spec.drawing.units,
                    "format": spec.drawing.format,
                    "parameters": spec.drawing.parameters,
                    "elements": spec.drawing.elements,
                },
                "metadata": spec.metadata,
            },
            source=str(args.spec),
        )

    result = run_job(spec)
    print(json.dumps(result.to_json(), indent=2, ensure_ascii=True))
    return 0
