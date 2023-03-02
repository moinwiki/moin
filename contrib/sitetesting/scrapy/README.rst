scappy crawler for moin
=======================

execute with::

   # default will crawl http://127.0.0.1:8080 
   scrapy crawl ref_checker 2>&1 | tee crawl.log

   # to specify another url starting point
   scrapy crawl -a url='https://my.wikihost.com/wiki_root/' ref_checker 2>&1 | tee crawl.log

once complete, the spider creates crawl.csv in the current directory, inspect this file for links with issues
