# SPDX-License-Identifier: EUPL-1.2
"""The disclaimer is the same in the engine (exports, /about) and in the interface (A8)."""

from pathlib import Path

from contracts.disclaimer import DISCLAIMER

I18N = Path(__file__).resolve().parents[2] / "frontend" / "src" / "i18n"


def test_the_interface_shows_the_same_disclaimer_as_the_engine() -> None:
    for language, text in DISCLAIMER.items():
        source = (I18N / f"{language}.ts").read_text(encoding="utf-8").replace("\\'", "'")
        assert text in source, language


def test_the_disclaimer_says_as_is_and_without_warranty() -> None:
    assert "« en l'état », sans garantie" in DISCLAIMER["fr"]
    assert '"as is", without warranty' in DISCLAIMER["en"]
