import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import fusion_lib as fl  # noqa: E402


@pytest.fixture(autouse=True)
def frame_1080p():
    """Every test starts from a 1920x1080 frame and a clean font-size cache."""
    fl.set_frame(1920, 1080)
    fl._K_CACHE.clear()
    yield
    fl.set_frame(1920, 1080)
    fl._K_CACHE.clear()


@pytest.fixture
def make_font(tmp_path):
    """Build a tiny TTF with chosen vertical metrics (needs fontTools)."""
    fb_mod = pytest.importorskip("fontTools.fontBuilder")
    pen_mod = pytest.importorskip("fontTools.pens.ttGlyphPen")

    def build(upm=1000, ascent=800, descent=-200, name="TestFont", cmap_chars="AB"):
        fb = fb_mod.FontBuilder(upm, isTTF=True)
        glyphs = [".notdef"] + [f"g{ord(c)}" for c in cmap_chars]
        fb.setupGlyphOrder(glyphs)
        fb.setupCharacterMap({ord(c): f"g{ord(c)}" for c in cmap_chars})
        pen = pen_mod.TTGlyphPen(None)
        pen.moveTo((0, 0))
        pen.lineTo((0, 500))
        pen.lineTo((400, 500))
        pen.closePath()
        glyph = pen.glyph()
        fb.setupGlyf({g: glyph for g in glyphs})
        fb.setupHorizontalMetrics({g: (500, 0) for g in glyphs})
        fb.setupHorizontalHeader(ascent=ascent, descent=descent)
        fb.setupNameTable({"familyName": name, "styleName": "Regular"})
        fb.setupOS2(sTypoAscender=ascent, sTypoDescender=descent, usWinAscent=ascent, usWinDescent=-descent)
        fb.setupPost()
        path = tmp_path / f"{name}-Regular.ttf"
        fb.save(str(path))
        return str(path)

    return build
