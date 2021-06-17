import scrapy
from scrapy.http import HtmlResponse
from avito_parse.items import AvitoParseItem
from scrapy.loader import ItemLoader


class AvitoSpider(scrapy.Spider):
    name = 'avito'
    allowed_domains = ['avito.ru']

    def __init__(self, mark):
        self.start_urls = ['https://www.avito.ru/sankt-peterburg/kvartiry/prodam-ASgBAgICAUSSA8YQ']

    def parse(self, response: HtmlResponse):
        ads_links = response.xpath('//a[@class="pagination-page"]/@href').extract()
        for link in ads_links:
            yield response.follow(link, callback=self.parse_ads)

    def parse_ads(self, response: HtmlResponse):
        name = response.css('h1.title-info-title span.title-info-title-text::text').extract.first()
        photos = response.xpath('//div[contains(@class,"gallery-img-wrapper")]//div[contains(@class, "gallery-img-frame")]/@data-url').extract()
        price = response.xpath('//span[@class="js-item-price"][1]/ text()').extract()

        yield AvitoParseItem(name=name, photos=photos, price=price)
        print(name, photos, price)
