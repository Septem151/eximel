"""Behavioural tests for the eximel interpreter (new file)."""
import io
from pathlib import Path

import pytest

from eximel.cli import run_script
from eximel.exceptions import EximelRuntimeError, EximelSyntaxError
from eximel.parser import Parser


def run(body: str) -> None:
    Parser(io.StringIO(f"<program>{body}</program>")).parse()


def test_falsy_variables_are_usable(capsys):
    run(
        '<decl name="z" type="int">0</decl>'
        '<decl name="e" type="str"></decl>'
        '<decl name="s"><add><var name="z"/><num>2</num></add></decl>'
        '<print usevars="true">z={z} s={s}</print>'
    )
    assert capsys.readouterr().out == "z=0 s=2\n"


@pytest.mark.parametrize(
    "op,expected",
    [("add", "9"), ("sub", "-3"), ("mult", "18"), ("div", "0.5")],
)
def test_operators(capsys, op, expected):
    run(
        f'<decl name="r"><{op}><num>3</num><num>6</num></{op}></decl>'
        '<print usevars="true">{r}</print>'
    )
    assert capsys.readouterr().out.strip() == expected


def test_nested_operations(capsys):
    run(
        '<decl name="r"><mult><add><num>1</num><num>2</num></add>'
        "<num>4</num></mult></decl>"
        '<print usevars="true">{r}</print>'
    )
    assert capsys.readouterr().out.strip() == "12"


def test_large_int_keeps_precision(capsys):
    run(
        '<decl name="r"><add><num>12345678901234567890</num><num>1</num></add></decl>'
        '<print usevars="true">{r}</print>'
    )
    assert capsys.readouterr().out.strip() == "12345678901234567891"


def test_substituted_values_not_rescanned(capsys):
    run(
        '<decl name="a" type="str">{b}</decl>'
        '<decl name="b" type="str">X</decl>'
        '<print usevars="true">{a}</print>'
    )
    assert capsys.readouterr().out.strip() == "{b}"


def test_division_by_zero():
    with pytest.raises(EximelRuntimeError):
        run("<decl name='r'><div><num>1</num><num>0</num></div></decl>")


def test_unknown_variable():
    with pytest.raises(EximelRuntimeError):
        run("<decl name='r'><add><var name='nope'/></add></decl>")


def test_non_numeric_variable_in_add():
    with pytest.raises(EximelRuntimeError):
        run(
            '<decl name="s" type="str">hi</decl>'
            '<decl name="r"><add><var name="s"/><num>1</num></add></decl>'
        )


def test_unknown_child_and_command_rejected():
    with pytest.raises(EximelSyntaxError):
        run("<decl name='r'><add><foo/></add></decl>")
    with pytest.raises(EximelSyntaxError):
        run("<bogus/>")


def test_cli_errors(tmp_path: Path):
    bad = tmp_path / "bad.xml"
    bad.write_text("<program>", encoding="utf-8")
    assert run_script(bad).status == 1
    assert run_script(tmp_path).status == 2
    assert run_script(tmp_path / "missing.xml").status == 2
    ent = tmp_path / "ent.xml"
    ent.write_text(
        '<!DOCTYPE p [<!ENTITY e "x">]><program><print>&e;</print></program>',
        encoding="utf-8",
    )
    assert run_script(ent).status == 1
    ok = tmp_path / "ok.xml"
    ok.write_text("<program><print>hi</print></program>", encoding="utf-8")
    assert run_script(ok).status == 0
