import re
from unittest.mock import Mock
from moin.cli.migration.moin19.import19 import PageRevision

def test_process_data_redirect():
    fake_self = Mock(spec=PageRevision)
    
    fake_self.backend = Mock()
    fake_self.backend.item_category_regex = re.compile(r"(?P<all>Category(?P<key>(?!Template)\S+))", re.UNICODE)
    
    fake_meta = {"contenttype": "text/x.moin.wiki;format=1.9;charset=utf-8"}
    old_data = "#REDIRECT MySecretPage"
    
    result = PageRevision._process_data(fake_self, fake_meta, old_data)
    
    expected = '[[MySecretPage|redirecting to MySecretPage ... |class="redirect"]]\n'

    assert result == expected, f"Error! {result}"