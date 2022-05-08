"""Lexer for eximel"""
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
        for cmd in program:
            if cmd.tag == "decl":
                var_name, var_value = self._parse_decl(cmd)
                self._variables[var_name] = var_value
            if cmd.tag == "print":
                self._parse_print(cmd)

    def _get_var(self, var_name: str) -> t.Any:
        variable = self._variables.get(var_name)
        if not variable:
            raise EximelRuntimeError(f"var {var_name} does not exist")
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
        if subcmd.tag == "add":
            variable = self._parse_add(subcmd)
            return var_name, variable
        return var_name, "COMPLEX"

    def _parse_add(self, cmd: Element) -> int | float:
        value: int | float = 0
        if len(cmd) == 0:
            raise EximelSyntaxError("add must have children")
        for subcmd in cmd:
            if subcmd.tag == "var":
                if subcmd.attrib.keys() != {"name"}:
                    raise EximelSyntaxError("Invalid var attributes")
                var_name = subcmd.attrib["name"]
                variable = self._get_var(var_name)
                value += variable
            elif subcmd.tag == "num":
                value += Parser._parse_num(subcmd)
            else:
                # handle function stuff here for add
                continue
        return value

    @staticmethod
    def _parse_num(cmd: Element) -> int | float:
        if len(cmd.attrib) != 0:
            raise EximelSyntaxError("num cannot have attributes")
        if not cmd.text:
            raise EximelSyntaxError("num must have a value present")
        try:
            val = float(cmd.text)
            if val.is_integer():
                return int(val)
            return val
        except ValueError as error:
            raise EximelRuntimeError("Invalid number in num") from error

    def _parse_print(self, cmd: Element) -> None:
        usevars_attr = cmd.attrib.get("usevars", "false")
        if usevars_attr not in {"true", "false"}:
            raise EximelRuntimeError("Invalid value for print usevars attribute")
        if usevars_attr == "true" and cmd.text:
            text = cmd.text
            for match in PRINT_REGEX.finditer(cmd.text):
                variable_match = match.group()
                variable = self._variables.get(variable_match[1:-1])
                if not variable:
                    raise EximelRuntimeError("Referenced unknown variable from print")
                text = text.replace(variable_match, str(variable))
            print(text.strip())
        elif not cmd.text:
            print()
        else:
            print(cmd.text.strip())
