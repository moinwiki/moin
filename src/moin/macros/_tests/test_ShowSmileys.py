# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Test for macros.ShowSmileys
"""

from moin.macros.ShowSmileys import Macro


def test_Macro():
    """test for Macro.macro"""
    expected_text = ["X-(", "angry", ":D", "biggrin", "<:(", "frown", "{o}", "star_off"]
    expected_tag = "{http://moinmo.in/namespaces/page}table-row"
    macro_obj = Macro()
    macro_out = macro_obj.macro("content", None, "page_url", "alternative")
    result_text = []
    result_tags = []
    for node in macro_out.iter_elements_tree():
        if getattr(node, "text"):
            result_text.append(getattr(node, "text"))
        if getattr(node, "tag"):
            result_tags.append(str(getattr(node, "tag")))
    assert set(expected_text).issubset(result_text)
    assert expected_tag in result_tags
