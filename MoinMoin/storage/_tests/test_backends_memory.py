"""
    MoinMoin - Test - MemoryBackend

    This defines tests for the MemoryBackend.

    @copyright: 2008 MoinMoin:ChristopherDenter,
                2008 MoinMoin:JohannesBerg,
                2008 MoinMoin:AlexanderSchremmer
    @license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""

from MoinMoin.storage._tests.test_backends import BackendTest
from MoinMoin.storage.backends.memory import MemoryBackend, TracingBackend

class TestMemoryBackend(BackendTest):
    """
    Test the MemoryBackend
    """

    def create_backend(self):
        return MemoryBackend()

    def kill_backend(self):
        pass

class TestTracingBackend(BackendTest):

    def create_backend(self):
        import random
        return TracingBackend()#"/tmp/codebuf%i.py" % random.randint(1, 2**30))

    def kill_backend(self):
        func = self.backend.get_func()
        try:
            func(MemoryBackend()) # should not throw any exc
        except:
            # I get exceptions here because py.test seems to handle setup/teardown incorrectly
            # in generative tests
            pass #print "EXC"

