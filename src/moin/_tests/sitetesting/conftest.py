import csv
import logging
import os
from pathlib import Path
import pytest
import signal
import subprocess
import sys
from time import sleep
from typing import List

try:
    from moin._tests.sitetesting import settings
except ImportError:
    from moin._tests.sitetesting import default_settings as settings
from moin._tests import check_connection
from moin._tests.sitetesting import CrawlResult


logger = logging.getLogger(__name__)


@pytest.fixture(scope="package")
def server():
    logger.info('starting server')
    server = None
    started = False
    cwd = os.getcwd()
    my_dir = os.path.dirname(__file__)
    os.chdir(my_dir)
    try:
        server_log = open('server.log', 'wb')
        flags = 0
        if sys.platform == 'win32':
            flags = subprocess.CREATE_NEW_PROCESS_GROUP  # needed for use of os.kill
        com = ['python', './run_moin.py']
        server = subprocess.Popen(com, stdout=server_log, stderr=subprocess.STDOUT,
                                  creationflags=flags)
        wait_count = 0
        while not started and wait_count < 12:
            wait_count += 1
            sleep(5)
            try:
                check_connection(9080)
            except Exception as e:
                logger.info(f'waiting for server startup {e}')
            else:
                started = True
    finally:
        os.chdir(cwd)

    if started:  # if not started, clean up now
        yield started

    if not server:  # unexpected error
        logger.error(f'server is {server}')
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
            logger.error('server not started. server.log:')
            os.chdir(my_dir)
            try:
                with open(server_log.name) as f:
                    logger.error(f.read())
            finally:
                os.chdir(cwd)
            yield started


def _scrapy_dir():
    my_dir = os.path.dirname(__file__)
    return os.path.join(my_dir, 'scrapy')


@pytest.fixture(scope="package")
def do_crawl(request):
    scrapy_dir = _scrapy_dir()
    Path(os.path.join(scrapy_dir, 'crawl.log')).touch()  # insure github workflow will have a file to archive
    Path(os.path.join(scrapy_dir, 'crawl.csv')).touch()
    server_started = True
    crawl_success = True
    if settings.SITE_HOST == '127.0.0.1:9080':
        server_started = request.getfixturevalue('server')
        if not server_started:
            crawl_success = False
    if server_started:
        logger.info('starting crawl')
        cwd = os.getcwd()
        os.chdir(scrapy_dir)
        try:
            com = ['scrapy', 'crawl', '-a', f'url={settings.CRAWL_START}', 'ref_checker']
            with open('crawl.log', 'wb') as crawl_log:
                p = subprocess.run(com, stdout=crawl_log, stderr=subprocess.STDOUT, timeout=600)
            if p.returncode != 0:
                crawl_success = False
            if not crawl_success:
                logger.error('crawl failed. crawl.log:')
                with open('crawl.log') as f:
                    logger.error(f.read())
        finally:
            os.chdir(cwd)
    return crawl_success


@pytest.fixture(scope="package")
def crawl_results(request) -> List[CrawlResult]:
    crawl_success = True
    if settings.DO_CRAWL:
        crawl_success = request.getfixturevalue('do_crawl')
    if crawl_success:
        try:
            with open(os.path.join(_scrapy_dir(), 'crawl.csv')) as f:
                in_csv = csv.DictReader(f)
                return [CrawlResult(**r) for r in in_csv]
        except Exception as e:
            crawl_success = False
            logger.error(f'exception reading crawl.csv {repr(e)}')
    if not crawl_success:
        logger.error('crawl failed')
        return []
