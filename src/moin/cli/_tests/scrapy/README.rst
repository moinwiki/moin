Scrapy crawler for Moin
=======================

This directory was created via ``scrapy startproject`` command,
then unneeded files were removed including items.py middlewares.py and pipelines.py.
See https://scrapy.org/ for details on scrapy.

Normal use is via ``pytest test_scrapy_crawl.py`` in parent directory

For manual execution of the crawl::

   # default will crawl http://127.0.0.1:8080
   scrapy crawl ref_checker 2>&1 | tee crawl.log

   # to specify another url starting point
   scrapy crawl -a url='https://my.wikihost.com/wiki_root/' ref_checker 2>&1 | tee crawl.log

Once complete, the spider creates crawl.csv and crawl.log in _test_artifacts at the root of the project.
