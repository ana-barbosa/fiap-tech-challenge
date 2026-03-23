import argparse
from pathlib import Path

from src import plan


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="VRP solver — plan routes or generate reports."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="Run the VRP genetic algorithm.")
    plan_parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to the TOML problem file (e.g. examples/att48.toml).",
    )
    plan_parser.add_argument(
        "--generations",
        type=int,
        default=None,
        help="Fixed generation cap. Overrides convergence and time limit.",
    )

    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.command == "plan":
        plan.run(input_path=args.input, generations=args.generations)


if __name__ == "__main__":
    main()
