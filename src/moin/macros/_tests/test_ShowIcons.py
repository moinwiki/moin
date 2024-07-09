# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Test for macros.ShowIcons
"""

import re
import os
from moin.macros.ShowIcons import Macro

my_dir = os.path.abspath(os.path.dirname(__file__))


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


def get_css_icon_names():
    """Read css file and search for icon urls"""
    css_file = os.path.join(os.path.split(my_dir)[0], "..", "static", "css", "common.css")
    with open(css_file, encoding="utf-8") as f:
        common_css = f.readlines()
    icon_list = set()
    for line in common_css:
        link = re.search(r"url\([\'\"]?([(.)/].*?)[\'\"]?\)", line)
        if link and link.group(0)[5:].startswith("../img/icons"):
            icon_list.add(link.group(0).split("/", 3)[3][:-2])
    return icon_list


def get_icon_filenames():
    """Scan img/icons dir for filenames"""
    icon_dir = os.path.join(os.path.split(my_dir)[0], "..", "static", "img", "icons")
    filenames = set()
    with os.scandir(icon_dir) as files:
        for file in files:
            if not file.name.startswith(".") and file.is_file():
                filenames.add(file.name)
    return filenames


def test_all_icon_files_exist():
    """Test if icons from css urls is a subset of filenames in icon dir"""
    icons = get_css_icon_names()
    files = get_icon_filenames()
    missing_icons = list(icons - files)
    assert not missing_icons
