"""Unit tests for fusion_lib: units verified in Resolve 21.2, name checks,
expression references, validation and Loader rendering."""
import pytest

import fusion_lib as fl


def val(tool, key):
    return tool.inputs[key].value


# ---------- units verified in Resolve (references/verified.md) ----------

def test_rect_mask_height_is_fraction_of_frame_height():
    m = fl.rect_mask("MaskA", 960, 540, 35, 35)
    assert val(m, "Width") == pytest.approx(35 / 1920, abs=1e-5)
    assert val(m, "Height") == pytest.approx(35 / 1080, abs=1e-5)


def test_rect_mask_unit_override_for_diagnostics():
    m = fl.rect_mask("MaskA", 960, 540, 800, 200, unit="width")
    assert val(m, "Height") == pytest.approx(200 / 1920, abs=1e-5)


def test_ellipse_mask_both_sides_are_fractions_of_frame_width():
    m = fl.ellipse_mask("MaskRing", 960, 540, 210, 210)
    assert val(m, "Width") == pytest.approx(210 / 1920, abs=1e-5)
    assert val(m, "Height") == pytest.approx(210 / 1920, abs=1e-5)


def test_ellipse_mask_outline_mode():
    m = fl.ellipse_mask("MaskRing", 960, 540, 210, 210, border_px=3.2)
    assert val(m, "Solid") == 0
    assert val(m, "BorderWidth") == pytest.approx(3.2 / 1920, abs=1e-6)


def test_transform_pivot_keeps_center_at_identity():
    xf = fl.transform("XfPop", "MrgIcon", pivot=(0.25, 0.3))
    assert val(xf, "Center") == (0.5, 0.5)
    assert val(xf, "Pivot") == (0.25, 0.3)


def test_center_conversion_y_up():
    assert fl.fx(960) == 0.5
    assert fl.fy(0) == 1.0
    assert fl.fy(1080) == 0.0


def test_vertical_frame():
    fl.set_frame(1080, 1920)
    m = fl.rect_mask("MaskA", 540, 960, 108, 192)
    assert val(m, "Width") == pytest.approx(0.1, abs=1e-5)
    assert val(m, "Height") == pytest.approx(0.1, abs=1e-5)
    assert val(m, "Center") == (0.5, 0.5)


# ---------- text size from font line height ----------

def test_font_line_height_reads_hhea(make_font):
    path = make_font(upm=1000, ascent=969, descent=-242)
    assert fl.font_line_height(path) == pytest.approx(1.211, abs=1e-3)


def test_text_size_k_follows_line_height(make_font, monkeypatch):
    inter_like = make_font(upm=2048, ascent=1984, descent=-494, name="InterLike")
    phosphor_like = make_font(upm=1024, ascent=960, descent=-64, name="PhosphorLike")
    paths = {"InterLike": inter_like, "PhosphorLike": phosphor_like}
    monkeypatch.setattr(fl, "_find_font", lambda family, style: paths.get(family))
    assert fl.text_size_k("InterLike") == pytest.approx(1.51, abs=0.01)
    assert fl.text_size_k("PhosphorLike") == pytest.approx(1.25, abs=0.01)


def test_text_size_k_falls_back_to_inter(monkeypatch):
    monkeypatch.setattr(fl, "_find_font", lambda family, style: None)
    assert fl.text_size_k("NoSuchFont") == fl.TEXT_SIZE_K


def test_text_size_uses_font_factor(monkeypatch):
    monkeypatch.setattr(fl, "text_size_k", lambda font, style="Regular": 2.0)
    t = fl.text("TxtA", "hi", 100, 100, 96, "#ffffff")
    assert val(t, "Size") == pytest.approx(96 / 1920 * 2.0, abs=1e-6)


def test_left_anchor_sets_left_justification():
    t = fl.text("TxtA", "a\nb", 100, 100, 40, "#ffffff", h_anchor=-1)
    assert val(t, "HorizontalJustificationNew") == 0
    c = fl.text("TxtB", "a", 100, 100, 40, "#ffffff", h_anchor=0)
    assert "HorizontalJustificationNew" not in c.inputs


# ---------- expression references ----------

def ref_names(expr):
    t = fl.Tool("TxtA", "TextPlus")
    t.set("StyledText", expr=expr)
    return t.refs()


def test_refs_ignore_lua_library_and_concatenation():
    expr = (': local s = TxtSource.StyledText.Value; '
            'for ch in string.gmatch(s, "[^a.b]") do out = out .. ch end; '
            'return Text(out .. "x.y")')
    assert ref_names(expr) == {"TxtSource", "string"}


def test_refs_ignore_member_chains_and_numbers():
    assert ref_names("Point(TxtPrice.Center.X + 0.5, 0.25)") == {"TxtPrice"}


def test_refs_found_in_links():
    m = fl.merge("MrgA", "BgA", "TxtA")
    assert m.refs() == {"BgA", "TxtA"}


# ---------- macro checks ----------

def simple_tools():
    return [fl.background("BgA", "#000000"), fl.text("TxtA", "a", 10, 10, 20, "#ffffff"),
            fl.merge("MrgOut", "BgA", "TxtA")]


def test_macro_renders_and_validates():
    src = fl.macro("TestMacro", simple_tools(), [fl.Publish("TxtA", "StyledText", "Text")], "MrgOut")
    assert fl.validate(src)
    assert 'MainOutput1 = InstanceOutput { SourceOp = "MrgOut"' in src


@pytest.mark.parametrize("bad, message", [
    ("Name", "reserved node name"),
    ("Text", "reserved node name"),
    ("1Bad", "bad node name"),
    ("Has Space", "bad node name"),
])
def test_macro_rejects_bad_names(bad, message):
    tools = simple_tools() + [fl.background(bad, "#000000")]
    with pytest.raises(ValueError, match=message):
        fl.macro("TestMacro", tools, [], "MrgOut")


def test_macro_rejects_duplicates():
    tools = simple_tools() + [fl.background("BgA", "#ffffff")]
    with pytest.raises(ValueError, match="duplicate node name 'BgA'"):
        fl.macro("TestMacro", tools, [], "MrgOut")


def test_macro_rejects_unknown_references():
    tools = simple_tools()
    tools[1].set("Size", 0.1, expr="XfMissing.TextScale*0.1")
    with pytest.raises(ValueError, match="unknown node 'XfMissing'"):
        fl.macro("TestMacro", tools, [], "MrgOut")


def test_macro_rejects_unknown_publish_and_output():
    with pytest.raises(ValueError, match="publish 'Size': unknown node 'TxtNope'"):
        fl.macro("TestMacro", simple_tools(), [fl.Publish("TxtNope", "Size")], "MrgOut")
    with pytest.raises(ValueError, match="output node 'MrgNope' not found"):
        fl.macro("TestMacro", simple_tools(), [], "MrgNope")


def test_publish_color_groups_four_channels():
    pubs = fl.publish_color("BgA", "TopLeft", "Background", 3)
    assert [p.source for p in pubs] == ["TopLeftRed", "TopLeftGreen", "TopLeftBlue", "TopLeftAlpha"]
    assert {p.group for p in pubs} == {3}
    assert pubs[0].name == "Background" and pubs[1].name is None


# ---------- validation ----------

@pytest.mark.parametrize("src, message", [
    ('{ "abc }', "unterminated string"),
    ("{ { }", "unclosed"),
    ("{ ) }", "unbalanced"),
    ('{ "a\nb" }', "newline inside string"),
])
def test_validate_catches_structure_errors(src, message):
    with pytest.raises(ValueError, match=message):
        fl.validate(src)


def test_validate_trailing_backslash_does_not_crash():
    with pytest.raises(ValueError, match="unterminated string"):
        fl.validate('{ "abc\\')


def test_lua_string_escaping_roundtrip():
    s = 'a "quoted"\nline \\ backslash'
    lua = pytest.importorskip("lupa").LuaRuntime()
    assert lua.eval(fl.lua_str(s)) == s


def test_macro_parses_as_lua():
    lupa = pytest.importorskip("lupa")
    src = fl.macro("TestMacro", simple_tools(), [], "MrgOut")
    err = lupa.LuaRuntime().eval("function(s) local f, e = load(s); return e end")("return " + src)
    assert err is None


# ---------- Loader ----------

def test_loader_renders_still_clip():
    ld = fl.loader("LdPhoto", "/tmp/photo.png")
    out = ld.render()
    assert 'Filename = "/tmp/photo.png"' in out
    assert 'FormatID = "PNGFormat"' in out
    assert "Loop = 0" in out and "GlobalStart = 0" in out and "GlobalEnd = 0" in out
    assert '["Clip1.PNGFormat.PostMultiply"]' in out


def test_loader_jpeg_format():
    assert 'FormatID = "JpegFormat"' in fl.loader("LdPhoto", "/tmp/photo.jpg").render()


def test_asset_path_is_under_assets_group(monkeypatch):
    monkeypatch.setattr(fl, "resolve_fusion_dirs", lambda: ["/base/Fusion"])
    assert fl.asset_path("Prog-time", "a.png") == "/base/Fusion/Assets/Prog-time/a.png"


# ---------- flow layout, tile colors, underlays, depth ----------

def _demo_graph():
    tools = [fl.background("BgCanvas", "#000000", alpha=0.0),
             fl.rect_mask("MaskCard", 300, 900, 400, 120),
             fl.background("BgCard", "#202020", mask="MaskCard"),
             fl.merge("MrgCard", "BgCanvas", "BgCard"),
             fl.text("TxtTitle", "Hi", 200, 900, 40, "#ffffff"),
             fl.merge("MrgTitle", "MrgCard", "TxtTitle"),
             fl.background("BgHolder", "#ff0000"),
             fl.transform("XfBlock", "MrgTitle"),
             fl.background("BgOut", "#000000", alpha=0.0),
             fl.merge("MrgOut", "BgOut", "XfBlock")]
    return tools


def test_layout_main_line_straight_and_branches_above():
    tools = fl.layout(_demo_graph(), "MrgOut", labels={"MrgCard": "Card", "MrgTitle": "Title"})
    by = {t.name: t for t in tools}
    # main line = heaviest input chain; the empty canvas is a branch above MrgCard
    main = ["MaskCard", "BgCard", "MrgCard", "MrgTitle", "XfBlock", "MrgOut"]
    assert all(by[n].pos[1] == 0 for n in main)
    xs = [by[n].pos[0] for n in main]
    assert xs == sorted(xs) and len(set(xs)) == len(xs)
    assert by["BgCanvas"].pos[1] < 0 and by["BgCanvas"].pos[0] <= by["MrgCard"].pos[0]
    assert by["TxtTitle"].pos[1] < 0 and by["BgOut"].pos[1] < 0
    assert by["BgHolder"].pos[1] > 0                       # wire-less helper below
    positions = [t.pos for t in tools if t.kind != "Underlay"]
    assert len(positions) == len(set(positions))           # no two nodes on one spot


def test_layout_underlays_and_tile_colors():
    tools = fl.layout(_demo_graph(), "MrgOut", labels={"MrgCard": "Card", "MrgTitle": "Title"})
    names = {t.name for t in tools if t.kind == "Underlay"}
    assert {"UlCard", "UlTitle", "UlOutput", "UlControls"} <= names
    by = {t.name: t for t in tools}
    assert by["TxtTitle"].tile == fl.BLOCK_COLORS["text"]
    assert by["MrgOut"].tile == fl.BLOCK_COLORS["output"]
    src = fl.macro("Demo", tools, [], "MrgOut")
    assert "UlCard = Underlay {" in src and "TileColor" in src
    assert fl.validate(src) is True


def test_layout_without_underlays(monkeypatch):
    monkeypatch.setattr(fl, "UNDERLAYS", False)
    tools = fl.layout(_demo_graph(), "MrgOut")
    assert not [t for t in tools if t.kind == "Underlay"]


def test_backgrounds_and_text_are_float16():
    assert val(fl.background("BgA", "#ffffff"), "Depth") == 3
    assert val(fl.text("TxtA", "a", 0, 0, 20, "#ffffff"), "Depth") == 3


def test_loader_is_a_plain_still_like_commercial_packs():
    # no timing inputs: the -1000..100000 / Hold variant lost the picture after a clip resize
    ld = fl.loader("LdA", "/tmp/a.png")
    for k in ("GlobalIn", "GlobalOut", "Loop", "HoldFirstFrame", "HoldLastFrame", "MissingFrames"):
        assert k not in ld.inputs


# ---------- images packed inside the .drfx (Setting:/) ----------

def test_asset_path_setting_mode():
    assert fl.asset_path("Grp", "a.png", mode="setting") == "Setting:/a.png"


def test_letterbox_fits_picture_into_box():
    lb = fl.letterbox("LbA", "LdA", 188, 188)
    assert val(lb, "Width") == 188 and val(lb, "Height") == 188 and val(lb, "Mode") == 1
    assert lb.inputs["Input"].src == "LdA"


def test_pack_puts_assets_next_to_setting(tmp_path):
    import zipfile
    from pack_drfx import pack
    st = tmp_path / "T.setting"
    st.write_text("{}")
    img = tmp_path / "src.png"
    img.write_bytes(b"png")
    out = tmp_path / "T.drfx"
    pack(str(out), [str(st)], "Grp", "Titles", assets={"t-icon.png": str(img)})
    names = zipfile.ZipFile(out).namelist()
    assert "Edit/Titles/Grp/t-icon.png" in names and "Edit/Titles/Grp/T.setting" in names


def test_pack_rejects_asset_paths_with_folders(tmp_path):
    from pack_drfx import pack
    st = tmp_path / "T.setting"
    st.write_text("{}")
    with pytest.raises(ValueError):
        pack(str(tmp_path / "T.drfx"), [str(st)], "Grp", assets={"../x.png": str(st)})
