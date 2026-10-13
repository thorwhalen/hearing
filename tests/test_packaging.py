"""The ``all`` extra really is "everything needed for the full app" (#31).

It used to list three packages by hand and silently omitted ``storage`` (dol),
so ``pip install 'hearing[all]'`` fell back to the dependency-free
``_FileTextStore``. ``all`` is now composed from the sibling extras; this pins
which ones, so leaving one out is a visible decision rather than drift.
"""

import re
from pathlib import Path

import pytest

try:
    import tomllib  # stdlib from 3.11
except ImportError:  # requires-python is 3.10
    tomllib = pytest.importorskip("tomli")

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"

#: Extras the full app needs. ``diarize``, ``openai``, ``vad`` and
#: ``fast-resample`` are optional alternatives, left out on purpose (see the
#: comment on ``all`` in pyproject.toml).
FULL_APP_EXTRAS = {"whisper", "agents", "capture", "http", "storage"}


def _extras() -> dict:
    return tomllib.loads(PYPROJECT.read_text())["project"]["optional-dependencies"]


def _self_extras(requirements: list) -> set:
    """Extras named by ``hearing[a,b]`` self-references in a requirement list."""
    found = set()
    for req in requirements:
        m = re.fullmatch(r"\s*hearing\[([^\]]+)\]\s*", req)
        if m:
            found |= {e.strip() for e in m.group(1).split(",")}
    return found


def test_all_composes_the_full_app_extras():
    assert _self_extras(_extras()["all"]) >= FULL_APP_EXTRAS


def test_all_includes_storage():
    """The regression in #31: without it, ``[all]`` never gets dol.TextFiles."""
    assert "storage" in _self_extras(_extras()["all"])


def test_every_extra_all_names_exists():
    extras = _extras()
    assert _self_extras(extras["all"]) <= set(extras) - {"all"}
