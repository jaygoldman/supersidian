"""Entry point for running Supersidian as a module or CLI command.

This module provides the CLI entry point that will be installed when users
run `pip install supersidian`. It can also be invoked directly with
`python -m supersidian`.

Usage:
    # Run as a module
    python -m supersidian

    # After pip install, run as a command
    supersidian
"""

from __future__ import annotations

from .supersidian import main


def cli() -> None:
    """CLI entry point installed by pip.

    This function is registered in pyproject.toml as the console script
    entry point, allowing users to run `supersidian` from the command line
    after installing the package.
    """
    main()


if __name__ == "__main__":
    main()
