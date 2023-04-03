import os
import pytest
import shutil

from moin._tests import get_dirs
from moin.cli._tests import run
from moin import log

logging = log.getLogger(__name__)


@pytest.fixture(scope="package")
def artifact_dir():
    """create and cd to and yield directory for wiki which persists thru all tests

    directory is deleted at end of all tests"""
    _, artifact_dir = get_dirs('cli')
    cwd = os.getcwd()
    os.chdir(artifact_dir)
    yield artifact_dir
    os.chdir(cwd)
    shutil.rmtree(artifact_dir)


@pytest.fixture
def artifact_dir2():
    """create and cd to and yield directory for wiki which gets deleted at end of each test function"""
    _, artifact_dir = get_dirs('cli2')
    cwd = os.getcwd()
    os.chdir(artifact_dir)
    yield artifact_dir
    os.chdir(cwd)
    shutil.rmtree(artifact_dir)


@pytest.fixture(scope="package")
def create_instance(artifact_dir):
    return run(['moin', 'create-instance'])


@pytest.fixture(scope="package")
def index_create(create_instance):
    return run(['moin', 'index-create', '-s', '-i'])


@pytest.fixture(scope="package")
def load_help(index_create):
    load_help_common = run(['moin', 'load-help', '-n', 'common'])
    # load_help_en = run(['moin', 'load-help', '-n', 'en'])  # see https://github.com/moinwiki/moin/issues/1378
    load_help_en = run(['echo', 'load help en disabled'])
    return load_help_common, load_help_en


@pytest.fixture
def create_instance2(artifact_dir2):
    return run(['moin', 'create-instance'])


@pytest.fixture
def index_create2(create_instance2):
    return run(['moin', 'index-create', '-s', '-i'])
