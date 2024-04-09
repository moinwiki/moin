# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.utils.send_file Tests
"""

import os
import tempfile
import shutil

import pytest

from moin.utils import send_file


class TestFuid:
    """test for send_file"""

    def setup_method(self, method):
        self.test_dir = tempfile.mkdtemp("", "test_dir")
        self.fname = os.path.join(self.test_dir, "test_file")

    def teardown_method(self, method):
        shutil.rmtree(self.test_dir)

    def makefile(self, fname, content):
        f = open(fname, "w")
        f.write(content)
        f.close()

    def test_temptest(self):
        self.makefile(self.fname, "test_content")
        result = send_file.send_file(self.fname, as_attachment=True, conditional=True)
        expected = "<Response streamed [200 OK]>"
        assert str(result) == expected

        with pytest.raises(TypeError):
            send_file.send_file(None, as_attachment=True)
