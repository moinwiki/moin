scrapy crawler for moin
=======================

this directory was created via ``scrapy startproject`` command,
then unneeded files were removed including items.py middlewares.py and pipelines.py
see https://scrapy.org/ for details on scrapy

normal use is via ``pytest test_scrapy_crawl.py`` in parent directory

for manual execution of the crawl::

   # default will crawl http://127.0.0.1:8080
   scrapy crawl ref_checker 2>&1 | tee crawl.log

   # to specify another url starting point
   scrapy crawl -a url='https://my.wikihost.com/wiki_root/' ref_checker 2>&1 | tee crawl.log

once complete, the spider creates crawl.csv and crawl.log in _test_artifacts at the root of the project
