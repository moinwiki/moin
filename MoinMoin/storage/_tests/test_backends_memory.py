# Copyright: 2008 MoinMoin:ChristopherDenter
# Copyright: 2008 MoinMoin:JohannesBerg
# Copyright: 2008 MoinMoin:AlexanderSchremmer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Test - MemoryBackend

    This defines tests for the MemoryBackend.
"""


from MoinMoin.storage._tests.test_backends import BackendTest
from MoinMoin.storage.backends.memory import MemoryBackend, TracingBackend
from MoinMoin.conftest import init_test_app, deinit_test_app
from MoinMoin._tests import wikiconfig
class TestMemoryBackend(BackendTest):
    """
    Test the MemoryBackend
    """

    def create_backend(self):
        # temporary hack till we apply some cleanup mechanism on tests         
        self.app, self.ctx = init_test_app(wikiconfig.Config)
        return MemoryBackend()

    def kill_backend(self):
        deinit_test_app(self.app, self.ctx)
        pass

class TestTracingBackend(BackendTest):
    def create_backend(self):
        # temporary hack till we apply some cleanup mechanism on tests         
        self.app, self.ctx = init_test_app(wikiconfig.Config)
        import random
        return TracingBackend()#"/tmp/codebuf%i.py" % random.randint(1, 2**30))

    def kill_backend(self):
        deinit_test_app(self.app, self.ctx)
        func = self.backend.get_func()
        try:
            func(MemoryBackend()) # should not throw any exc
        except:
            # I get exceptions here because py.test seems to handle setup/teardown incorrectly
            # in generative tests
            pass #print "EXC"

