#!/usr/bin/env python

import os
import shutil
from subprocess import run


def main():
    cwd = os.getcwd()
    try:
        os.chdir(os.path.dirname(__file__))
        coms = [
                ['moin', 'index-create', '-s', '-i'],
                ['moin', 'load', '--file', '../../../../src/moin/contrib/sample-backup.moin'],
                ['moin', 'index-build'],
                ['moin', 'run', '-p', '9080']
               ]
        for com in coms:
            run(com)
    finally:
        shutil.rmtree('wiki')
        os.chdir(cwd)


if __name__ == '__main__':
    main()
