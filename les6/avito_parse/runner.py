from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings

from avito_parse.spiders.avito import AvitoSpider
from avito_parse import settings

if __name__ == '__main__':
    crawler_settings = Settings()
    crawler_settings.setmodule(settings)
    process = CrawlerProcess(settings=crawler_settings)
    process.crawl(AvitoSpider, mark='mark')
    process.start()
