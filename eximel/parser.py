"""Lexer for eximel"""
import math
import re
import typing as t
from io import TextIOWrapper
from xml.etree.ElementTree import Element, ElementTree

from defusedxml.ElementTree import parse as xmlparse

from eximel.exceptions import EximelRuntimeError, EximelSyntaxError

TYPE_TABLE: dict[str, t.Any] = {
    "int": int,
    "float": float,
    "str": str,
    "infer": t.Any,
}

OPERATORS = {"add", "sub", "mult", "div"}

PRINT_REGEX = re.compile(r"\{([^\\\}]*)\}", re.MULTILINE)


class Parser:
    """tokenizes a string for eXiMeL parsing.

    Args:
        file: the eXiMeL script to perform operations on.
    """

    def __init__(self, file: TextIOWrapper) -> None:
        self._file = file
        self._xml: ElementTree = xmlparse(file)
        self._variables: dict = {}

    def parse(self) -> None:
        program = self._xml.getroot()
        if program is None or program.tag != "program":
            raise EximelSyntaxError("Root element must be <program>")
        for cmd in program:
            if cmd.tag == "decl":
                var_name, var_value = self._parse_decl(cmd)
                self._variables[var_name] = var_value
            elif cmd.tag == "print":
                self._parse_print(cmd)
            else:
                raise EximelSyntaxError(f"Unknown command <{cmd.tag}>")

    def _get_var(self, var_name: str) -> t.Any:
        # a variable may legitimately hold a falsy value (0, 0.0, ""), so test
        # for membership rather than truthiness
        if var_name not in self._variables:
            raise EximelRuntimeError(f"var {var_name} does not exist")
        variable = self._variables[var_name]
        if variable is None:
            raise EximelRuntimeError(f"var {var_name} has no value")
        return variable

    def _parse_decl(self, cmd: Element) -> tuple[str, t.Any]:
        if "name" not in cmd.attrib:
            raise EximelSyntaxError("Missing decl name")
        var_name = cmd.attrib["name"]
        var_type = cmd.attrib.get("type", "infer")
        if var_type not in TYPE_TABLE:
            raise EximelSyntaxError("Invalid decl type")
        if len(cmd) == 0:
            if not cmd.text:
                return var_name, None
            if var_type == "infer":
                raise EximelSyntaxError(
                    "Cannot infer decl type without children elements"
                )
            try:
                typecast = TYPE_TABLE[var_type]
                variable = typecast(cmd.text)
            except ValueError as error:
                raise EximelRuntimeError("Invalid decl value for given type") from error
            return var_name, variable
        if len(cmd) != 1:
            raise EximelSyntaxError("Inferred decl contains more than 1 child")
        subcmd = cmd[0]
        if subcmd.tag not in OPERATORS:
            raise EximelSyntaxError("Invalid operator as decl child")
        return var_name, self._parse_operation(subcmd)

    def _parse_operand(self, cmd: Element) -> int | float:
        if cmd.tag == "var":
            if cmd.attrib.keys() != {"name"}:
                raise EximelSyntaxError("Invalid var attributes")
            variable = self._get_var(cmd.attrib["name"])
            if isinstance(variable, bool) or not isinstance(variable, (int, float)):
                raise EximelRuntimeError(
                    f"var {cmd.attrib['name']} is not a number"
                )
            return variable
        if cmd.tag == "num":
            return Parser._parse_num(cmd)
        if cmd.tag in OPERATORS:
            return self._parse_operation(cmd)
        raise EximelSyntaxError(f"Invalid operand <{cmd.tag}>")

    def _parse_operation(self, cmd: Element) -> int | float:
        if len(cmd) == 0:
            raise EximelSyntaxError(f"{cmd.tag} must have children")
        operands = [self._parse_operand(subcmd) for subcmd in cmd]
        value = operands[0]
        if cmd.tag == "add":
            for operand in operands[1:]:
                value += operand
        elif cmd.tag == "sub":
            for operand in operands[1:]:
                value -= operand
        elif cmd.tag == "mult":
            for operand in operands[1:]:
                value *= operand
        else:  # div
            for operand in operands[1:]:
                if operand == 0:
                    raise EximelRuntimeError("Division by zero")
                value /= operand
            if isinstance(value, float) and value.is_integer():
                value = int(value)
        return value

    @staticmethod
    def _parse_num(cmd: Element) -> int | float:
        if len(cmd.attrib) != 0:
            raise EximelSyntaxError("num cannot have attributes")
        if not cmd.text or not cmd.text.strip():
            raise EximelSyntaxError("num must have a value present")
        text = cmd.text.strip()
        try:
            # try int first so large integers keep full precision
            return int(text)
        except ValueError:
            pass
        try:
            val = float(text)
        except ValueError as error:
            raise EximelRuntimeError("Invalid number in num") from error
        if not math.isfinite(val):
            raise EximelRuntimeError("Invalid number in num")
        if val.is_integer():
            return int(val)
        return val

    def _parse_print(self, cmd: Element) -> None:
        usevars_attr = cmd.attrib.get("usevars", "false")
        if usevars_attr not in {"true", "false"}:
            raise EximelRuntimeError("Invalid value for print usevars attribute")
        if usevars_attr == "true" and cmd.text:

            def substitute(match: re.Match) -> str:
                name = match.group(1)
                if name not in self._variables:
                    raise EximelRuntimeError("Referenced unknown variable from print")
                variable = self._variables[name]
                if variable is None:
                    raise EximelRuntimeError(f"var {name} has no value")
                return str(variable)

            # single pass: substituted values are never re-scanned
            print(PRINT_REGEX.sub(substitute, cmd.text).strip())
        elif not cmd.text:
            print()
        else:
            print(cmd.text.strip())
