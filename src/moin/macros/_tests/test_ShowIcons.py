# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Test for macros.ShowIcons
"""

from moin.macros.ShowIcons import Macro


def test_ShowIconsMacro():
    """Call ShowIcons macro and test output"""
    test_icons = ["admon-note", "angry", "biggrin", "frown", "moin-rss", "smile3", "star_off"]
    expected_namespace = "{http://moinmo.in/namespaces/page}"
    expected_tags = set(f"{expected_namespace}{el_name}" for el_name in ["table", "table-header", "table-row"])
    expected_texts = set(f"<<Icon({icon_name}.png)>>" for icon_name in test_icons)
    expected_paths = set(f"/static/img/icons/{icon_name}.png" for icon_name in test_icons)
    macro_obj = Macro()
    macro_out = macro_obj.macro("content", None, "page_url", "alternative")
    result_tags = set()
    result_texts = set()
    result_paths = set()
    for node in macro_out.iter_elements_tree():
        if getattr(node, "tag"):
            result_tags.add(str(getattr(node, "tag")))
        if getattr(node, "text"):
            result_texts.add(getattr(node, "text"))
        if getattr(node, "attrib"):
            result_paths.update(getattr(node, "attrib").values())
    assert expected_tags.issubset(result_tags)
    assert expected_texts.issubset(result_texts)
    assert expected_paths.issubset(result_paths)
