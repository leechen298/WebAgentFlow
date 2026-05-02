"""Top-level ``wagent`` dispatcher.

    wagent verify [args]
    wagent skill install [args]
    wagent skill uninstall [args]

Kept intentionally thin — each subcommand module owns its own argparse
configuration and business logic; main.py just wires them together so a
future subcommand (e.g. ``wagent spec list``) can slot in the same way.
"""

from __future__ import annotations

import argparse
import sys

from wagent import __version__, skill, verify


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wagent",
        description=(
            "WebAgentFlow CLI — verify scenarios via the HTTP API and "
            "manage the Claude Code skill."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # wagent verify
    verify_parser = subparsers.add_parser(
        "verify",
        help="Run a scenario via /exploration/autonomous-runs.",
    )
    verify.configure_parser(verify_parser)
    verify_parser.set_defaults(func=verify.run)

    # wagent skill {install,uninstall}
    skill_parser = subparsers.add_parser(
        "skill",
        help="Manage the Claude Code skill.",
    )
    skill_sub = skill_parser.add_subparsers(dest="skill_command", required=True)

    install_parser = skill_sub.add_parser(
        "install",
        help=(
            "Write verify-scenario skill files into Claude Code's "
            "skill directory."
        ),
    )
    skill.configure_install_parser(install_parser)
    install_parser.set_defaults(func=skill.run_install)

    uninstall_parser = skill_sub.add_parser(
        "uninstall",
        help="Remove the verify-scenario skill files.",
    )
    skill.configure_uninstall_parser(uninstall_parser)
    uninstall_parser.set_defaults(func=skill.run_uninstall)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
