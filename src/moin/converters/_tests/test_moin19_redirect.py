import pytest

from moin.cli.migration.moin19._utils19 import split_body
from moin.converters.moinwiki19_in import ConverterFormat19
from moin.converters.moinwiki_out import Converter as MoinwikiOut
from moin.utils.tree import html, moin_page, xlink


def convert(text):
    return ConverterFormat19()(text)


def find_links(tree):
    return [el for el in tree.iter() if not isinstance(el, str) and el.tag == moin_page.a]


@pytest.mark.parametrize("text", ["#REDIRECT TargetPage\n", "#redirect TargetPage\n"])
def test_redirect_becomes_link(text):
    links = find_links(convert(text))
    assert len(links) == 1
    link = links[0]
    assert str(link.get(xlink.href)) == "wiki.local:TargetPage"
    assert link.get(html.class_) == "redirect"


def test_redirect_in_middle_of_text_is_not_a_link():
    tree = convert("To get help, please see #REDIRECT Home\n")
    assert not any(link.get(html.class_) == "redirect" for link in find_links(tree))


def test_redirect_output_keeps_class():
    out = MoinwikiOut()(convert("#REDIRECT TargetPage\n"))
    assert out == '[[TargetPage|redirecting to TargetPage ...|class="redirect"]]\n'


def test_split_body_keeps_redirect_in_body():
    assert split_body("#REDIRECT Home\n") == ({}, "#REDIRECT Home\n")


def test_split_body_keeps_redirect_after_other_instructions():
    pi, body = split_body("#format wiki\n#REDIRECT Home\n")
    assert pi == {"format": "wiki"}
    assert body == "#REDIRECT Home\n"


def test_split_body_still_extracts_other_instructions():
    pi, body = split_body("#acl All:read\nHello\n")
    assert pi == {"acl": "All:read"}
    assert body == "Hello\n"
