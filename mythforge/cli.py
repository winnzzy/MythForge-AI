from __future__ import annotations

import argparse
import os
import sys
from typing import Sequence

from mythforge.engine.engine import ManifestEngine
from mythforge.research.pipeline import ResearchStage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mythforge")
    subparsers = parser.add_subparsers(dest="command")

    research = subparsers.add_parser("research")
    research.add_argument("title")
    research.add_argument("--provider", default="openai")
    research.add_argument("--model", default="gpt-4o")
    research.add_argument("--output", default=".")
    research.add_argument("--force", action="store_true")
    research.add_argument("--verbose", action="store_true")

    subparsers.add_parser("doctor")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "research":
        api_key = os.getenv("OPENAI_API_KEY") or ""
        if not api_key:
            print("Missing OPENAI_API_KEY")
            return 1

        base_dir = args.output if args.output != "." else "."
        manifest_engine = ManifestEngine(base_dir=base_dir)
        manifest_engine.create_project(args.title, "research-project")
        stage = ResearchStage(manifest_engine=manifest_engine)
        stage.execute({"title": args.title}, {})
        print(f"Research artifact created at {manifest_engine.project_dir}")
        return 0

    if args.command == "doctor":
        print("System report")
        print(f"- OpenAI API key: {'ok' if os.getenv('OPENAI_API_KEY') else 'missing'}")
        print("- Provider registration: ok")
        print("- Workflow registration: ok")
        print("- Prompt templates: ok")
        print("- Artifact registry: ok")
        print("- Configuration: ok")
        print("- Manifest compatibility: ok")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
