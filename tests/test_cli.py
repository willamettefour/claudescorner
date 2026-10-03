import os
import subprocess
import sys
from pathlib import Path

from PIL import Image

from claudescorner import __version__
from claudescorner.cli import main

SRC = Path(__file__).resolve().parents[1] / "src"


def test_valid_hex_color(capsys):
    assert main(["#FF5733"]) == 0
    assert capsys.readouterr().out == "'#FF5733' is a valid color (hex) -> RGB (255, 87, 51)\n"


def test_valid_rgb_tuple(capsys):
    assert main(["255, 87, 51"]) == 0
    assert capsys.readouterr().out == "'255, 87, 51' is a valid color (rgb_tuple) -> RGB (255, 87, 51)\n"


def test_invalid_color_exits_1(capsys):
    assert main(["not a color"]) == 1
    assert capsys.readouterr().out == (
        "'not a color' is NOT valid: not a recognized hex code or RGB tuple\n"
    )


def test_empty_argument_is_an_invalid_color(capsys):
    assert main([""]) == 1
    assert "empty string" in capsys.readouterr().out


def test_no_arguments_runs_the_demo(capsys):
    assert main([]) == 0
    out = capsys.readouterr().out
    assert out.startswith("INPUT")
    assert "to_rgb_tuple examples:" in out


def test_help_and_version(capsys):
    assert main(["--help"]) == 0
    assert capsys.readouterr().out.startswith("usage: claudescorner")
    assert main(["-h"]) == 0
    capsys.readouterr()
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == "claudescorner " + __version__


def test_glass_demo_writes_an_image(tmp_path, capsys):
    out = tmp_path / "card.png"
    assert main(["--glass-demo", str(out)]) == 0
    assert "wrote" in capsys.readouterr().out
    with Image.open(out) as card:
        assert card.size == (539, 306)


def test_python_dash_m_entry_point():
    paths = [str(SRC)] + ([os.environ["PYTHONPATH"]] if os.environ.get("PYTHONPATH") else [])
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(paths))
    done = subprocess.run(
        [sys.executable, "-m", "claudescorner", "#FF5733"],
        capture_output=True, text=True, env=env,
    )
    assert done.returncode == 0
    assert "(255, 87, 51)" in done.stdout
