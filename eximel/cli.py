"""CLI Module for eximel"""
import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from xml.etree.ElementTree import ParseError

from eximel import __version__, _description
from eximel.exceptions import EximelError
from eximel.parser import Parser

_prog = Path(sys.argv[0]).name


@dataclass
class _CLIExit:
    def __init__(self, status: int, message: str | None = None) -> None:
        self.status = status
        if message:
            self.message = f"{message}\n"
            if status != 0:
                self.message = f"{_prog}: error: " + self.message


def run_script(script: Path) -> _CLIExit:
    """runs an eximel script file.

    reads in an eximel file, runs through a lexer, parses the tokens,
    then runs the script.

    Args:
        script: path to the script to run.

    Returns:
        _CLIExit: a status code indicating whether the script ran successfully,
            with an optional message indicating a reason for failure.
    """
    if not script.exists():
        return _CLIExit(2, f"{script}: No such file or directory")
    with open(script, "r", encoding="utf-8") as file:
        try:
            parser = Parser(file)
            parser.parse()
        except ParseError:
            return _CLIExit(1, f"{script}: Not in valid XML format")
        except EximelError as error:
            return _CLIExit(1, f"{script}: {error}")
    return _CLIExit(0)


def main() -> None:
    """CLI Entrypoint"""
    parser = argparse.ArgumentParser(description=_description, prog=_prog)
    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "script", action="store", type=Path, help="path to eXiMeL script"
    )
    args = parser.parse_args()
    script: Path = args.script
    parser.exit(**vars(run_script(script)))
