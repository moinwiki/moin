# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.cli pytest fixtures

Common fixtures for tests

fixtures are used for

* management of temporary directory under moin/_test_artifacts
  which holds the test wiki instance
* handling dependencies between cli commands
  for example, index-create requires create-instance

package scope fixtures used for efficiency in load-help and dump-help tests
each cli command is executed only once
while the tests are written one each per command
"""

import csv
import os
import pytest
import shutil
import signal
import subprocess
import sys
from time import sleep
from typing import List

from moin._tests import check_connection, get_dirs
from moin.cli._tests import run
from moin.cli._tests.scrapy.moincrawler.items import CrawlResult
from moin import log
try:
    from moin.cli._tests import settings
except ImportError:
    from moin.cli._tests import default_settings as settings

logging = log.getLogger(__name__)


@pytest.fixture(scope="package")
def artifact_dir():
    """create and cd to and yield directory for wiki which persists thru all tests

    directory is deleted at end of all tests"""
    _, artifact_dir = get_dirs('cli')
    cwd = os.getcwd()
    os.chdir(artifact_dir)
    logging.info(f'artifact_dir = {str(artifact_dir)}')
    yield artifact_dir
    os.chdir(cwd)
    shutil.rmtree(artifact_dir)


@pytest.fixture
def artifact_dir2():
    """create and cd to and yield directory for wiki which gets deleted at end of each test function"""
    _, artifact_dir = get_dirs('cli2')
    cwd = os.getcwd()
    os.chdir(artifact_dir)
    logging.info(f'artifact_dir = {str(artifact_dir)}')
    yield artifact_dir
    os.chdir(cwd)
    shutil.rmtree(artifact_dir)


@pytest.fixture(scope="package")
def create_instance(artifact_dir):
    return run(['moin', 'create-instance'])


@pytest.fixture(scope="package")
def index_create(create_instance):
    return run(['moin', 'index-create'])


@pytest.fixture(scope="package")
def load_help(index_create):
    load_help_common = run(['moin', 'load-help', '-n', 'common'])
    load_help_en = run(['moin', 'load-help', '-n', 'en'])
    return load_help_common, load_help_en


@pytest.fixture(scope="package")
def welcome(index_create):
    return run(['moin', 'welcome'])


def get_crawl_server_log_path():
    _, artifact_base_dir = get_dirs('')
    return artifact_base_dir / 'server-crawl.log'


@pytest.fixture(scope="package")
def server(welcome, load_help, artifact_dir):
    run(['moin', 'index-build'])
    started = False
    server_log = open(get_crawl_server_log_path(), 'wb')
    server = run(['moin', 'run', '-p', '9080'], server_log, wait=False)
    wait_count = 0
    while not started and wait_count < 12:
        wait_count += 1
        sleep(5)
        try:
            check_connection(9080)
        except Exception as e:
            logging.info(f'waiting for server startup {e}')
        else:
            started = True

    if started:  # if not started, clean up now
        yield started

    if not server:  # unexpected error
        logging.error(f'server is {server}')
        yield False
    else:
        if sys.platform == "win32":
            os.kill(server.pid, signal.CTRL_C_EVENT)
        else:
            server.send_signal(signal.SIGINT)
        try:
            server.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.communicate()
        server_log.close()
        if not started:
            logging.error('server not started. server.log:')
            try:
                with open(server_log.name) as f:
                    logging.error(f.read())
            except IOError as e:
                logging.error(f'{repr(e)} when trying to open server log')
            yield started


@pytest.fixture(scope="package")
def do_crawl(request, artifact_dir):
    moin_dir, artifact_base_dir = get_dirs('')
    (artifact_base_dir / 'crawl.log').touch()  # insure github workflow will have a file to archive
    (artifact_base_dir / 'crawl.csv').touch()
    server_started = True
    crawl_success = True
    if settings.SITE_HOST == '127.0.0.1:9080':
        server_started = request.getfixturevalue('server')
        if not server_started:
            crawl_success = False
    if server_started:
        logging.info('starting crawl')
        os.chdir(moin_dir / 'src' / 'moin' / 'cli' / '_tests' / 'scrapy')
        try:
            com = ['scrapy', 'crawl', '-a', f'url={settings.CRAWL_START}', 'ref_checker']
            with open(artifact_dir / 'crawl.log', 'wb') as crawl_log:
                p = run(com, crawl_log, timeout=600)
            if p.returncode != 0:
                crawl_success = False
            if not crawl_success:
                logging.error('crawl failed. crawl.log:')
                with open('crawl.log') as f:
                    logging.error(f.read())
        finally:
            os.chdir(artifact_dir)
    return crawl_success


@pytest.fixture(scope="package")
def crawl_results(request, artifact_dir) -> List[CrawlResult]:
    _, artifact_base_dir = get_dirs('')
    crawl_success = True
    if settings.DO_CRAWL:
        crawl_success = request.getfixturevalue('do_crawl')
    if crawl_success:
        try:
            with open(artifact_base_dir / 'crawl.csv') as f:
                in_csv = csv.DictReader(f)
                return [CrawlResult(**r) for r in in_csv]
        except Exception as e:
            crawl_success = False
            logging.error(f'exception reading crawl.csv {repr(e)}')
    if not crawl_success:
        logging.error('crawl failed')
        return []


@pytest.fixture(scope="package")
def server_crawl_log(crawl_results):
    if not settings.DO_CRAWL:
        logging.warn('using existing server-crawl.log')
    return get_crawl_server_log_path()


@pytest.fixture
def create_instance2(artifact_dir2):
    return run(['moin', 'create-instance'])


@pytest.fixture
def index_create2(create_instance2):
    return run(['moin', 'index-create'])
