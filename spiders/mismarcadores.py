import scrapy
import time

from selenium import webdriver
from sport_stats.items import SportStatsItem
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
# from selenium.common.exceptions import TimeoutException


class MisMarcadoresSpider(scrapy.Spider):
    name = "mismarcadores"
    base_url = 'https://www.mismarcadores.com'
    start_urls = [base_url + '/futbol/']

    def __init__(self, sport=""):
        self.driver = webdriver.Firefox()
        self.main_window_handle = None
        # self.start_urls = [ % sport]

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(MisMarcadoresSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=scrapy.signals.spider_closed)
        return spider

    def spider_closed(self, spider):
        self.driver.close()
        self.driver.stop_client()

    def parse(self, response):
        league_links = "//ul[@class='menu country-list']/li/ul[@class='submenu hidden']/li/a/@href"
        resources = response.xpath(league_links).extract()

        for resource in resources[1:2]:
            url = self.base_url + resource + "archivo/"
            print url
            yield scrapy.Request(url=url, callback=self.parse_league)

    """
    parse_event: Parses elements in events table
    @returns [Statistics] Statistics of a match
    """
    def parse_event(self, element):
        print "PARSE_EVENT"
        if len(element.find_elements_by_xpath(".//*")) == 0:
            print "EMPTY"
            return

        event = {}
        icon_box = element.find_element_by_xpath(".//*[contains(@class,'icon-box')]")
        considered_events = ['soccer-ball', 'y-card', 'r-card', 'penalty-missed']
        event["event"] = icon_box.get_attribute("class").split()[1]
        if event["event"] not in considered_events:
            return

        event["time"] = element.find_element_by_xpath(".//*[contains(@class,'time-box')]").text
        event["participant"] = element.find_element_by_xpath(".//*[contains(@class,'participant')]").text

        try:
            event["assist"] = element.find_element_by_xpath(".//*[contains(@class,'assist')]").text
        except NoSuchElementException:
            event["assist"] = ""

        return event

    def parse_events(self, response):
        self.driver.get(response.url)
        print "DEBUG"
        path = "//*[@id='parts']//td[contains(@class, 'summary-vertical')]/*[@class='wrapper']"
        events_list = self.driver.find_elements_by_xpath(path)
        print events_list
        events = []

        item = SportStatsItem()
        # events = [self.parse_detail(elem) for elem in events_list]
        for event in events_list:
            print event
            info = self.parse_event(event)
            if info is not None:
                events.append(info)
        item['extra'] = events
        print item
        return item

    def parse_stat(self, stat):
        stat_name_path = "//td[@class='score stats']"
        home_stat_path = "//td[contains(@class, 'fl')]/div"
        away_stat_path = "//td[contains(@class, 'fr')]/div"

        return {
            "name": self.driver.find_elements_by_xpath(stat_name_path).text,
            "local": self.driver.find_elements_by_xpath(home_stat_path).text,
            "away": self.driver.find_elements_by_xpath(away_stat_path).text
        }

    def parse_stats(self):
        # Make visible the statistics content
        tab_path = "//*[@id='a-match-statistics']"
        self.driver.find_elements_by_xpath(tab_path).click()

        path = "//*[@id='tab-statistics-0-statistic']"
        stats_list = self.driver.find_elements_by_xpath(path)
        print stats_list
        stats = []

        for stat in stats_list:
            info = self.parse_stat(stat)
            if info is not None:
                stats.append(info)
        return stats

    """
    parse_result: Parses the info on a list element containing results
    @returns [Result] Info of a match's result
    """
    def parse_result(self, element):
        item = SportStatsItem()
        sections = element.find_elements_by_xpath("td")
        fields = ['time', 'team-home', 'team-away', 'score']
        for section in sections:
            class_chunks = section.get_attribute('class').split()
            if len(class_chunks) > 1 and class_chunks[1] in fields:
                item[class_chunks[1].replace('-', '_')] = section.text
        return item

    def parse_season(self, response):
        self.driver.get(response.url)
        self.main_window_handle = self.driver.current_window_handle

        # Click on show more till every result is visible
        show_more_path = "//*[@id='tournament-page-results-more']//a"
        while True:
            try:
                elems = self.driver.find_elements_by_xpath(show_more_path)
                self.driver.execute_script("arguments[0].scrollIntoView();", elems[0])
                elems[0].click()
                time.sleep(1)
            except Exception:
                # Create HtmlResponse object from driver current HTML
                html = scrapy.http.HtmlResponse(url=response.url, body=self.driver.page_source, encoding='utf-8')
                results_path = "//div[@id='fs-results']//tbody/tr/@id"
                results = html.xpath(results_path).extract()
                break

        for result in results:
            if len(result.split('_')) < 3:
                continue
            match_id = result.split('_')[2]
            url = self.base_url + "/partido/" + match_id
            summary_url = url + "/#resumen-del-partido"
            stats_url = url + "/#estadisticas-del-partido;0"
            print url
            yield scrapy.Request(url=summary_url, callback=self.parse_events)

    def parse_league(self, response):
        year_links = "//*[@id='tournament-page-archiv']//td[1]/a/@href"
        resources = response.xpath(year_links).extract()
        print resources

        for resource in resources:
            url = self.base_url + resource + "resultados"
            print url
            yield scrapy.Request(url=url, callback=self.parse_season)
