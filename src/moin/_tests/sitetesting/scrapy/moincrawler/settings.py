# Scrapy settings for moincrawler project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = 'moincrawler'

SPIDER_MODULES = ['moin._tests.sitetesting.scrapy.moincrawler.spiders']
NEWSPIDER_MODULE = 'moin._tests.sitetesting.scrapy.moincrawler.spiders'
# Obey robots.txt rules
ROBOTSTXT_OBEY = True
