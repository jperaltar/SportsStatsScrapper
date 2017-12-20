# -*- coding: utf-8 -*-

import scrapy
import time

from selenium import webdriver
from sport_stats.items import SportStatsItem
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException


class MisMarcadoresSpider(scrapy.Spider):
    name = "mismarcadores"
    base_url = 'https://www.mismarcadores.com'
    start_urls = [base_url + '/futbol/']

    # EVENTS CONSTANTS
    # Dictionary to translate event icons names to final event names
    SUBSTITUTION_EVENT_TYPE = 'player_substitution'
    MATCH_EVENTS = {
        "soccer-ball": "goal",
        "y-card": "yellow_card",
        "r-card": "red_card",
        "ry-card": "second_yellow_card",
        "penalty-missed": "penalty_missed",
        "substitution-in": SUBSTITUTION_EVENT_TYPE
    }

    # SATISTICS CONSTANTS
    MATCH_STATS = {
        "Paradas": "saves",
        "Córneres": "corners",
        "Remates": "shots",
        "Remates fuera": "shots_out",
        "Posesión de balón": "ball_control",
        "Faltas": "fouls",
        "Fueras de juego": "offsides",
        "Remates rechazados": "deflected_shots",
        "Remates a puerta": "shots_on_goal",
        "Tarjetas amarillas": "yellow_cards",
        "Tarjetas rojas": "red_cards"
    }

    # SATISTICS CONSTANTS
    MATCH_INDIVIDUAL_STATS = {
        "Asistencias": "assists",
        "Faltas cometidas": "fouls",
        "% Acierto en pases": "pass_success",
        "Pases totales": "total_passes",
        "Tarjetas amarillas": "yellow_cards",
        "Remates": "shots",
        "Faltas recibidas": "received_fouls",
        "Fueras de juego": "offsides",
        "Rechaces": "deflections",
        "Goles": "goals",
        "Tarjetas rojas": "red_cards",
        "Remates a puerta": "shots_on_goal"
    }

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
            yield scrapy.Request(url=url, callback=self.parse_league)

    """
    parse_event: Parses elements in events table
    @returns [Statistics] Statistics of a match
    """
    def parse_event(self, event_html):
        if len(event_html.xpath(".//*").extract()) == 0:
            return None

        event = {}
        icon_box = event_html.css(".icon-box")
        event["type"] = icon_box.xpath("@class").extract()[0].split()[1]
        if event["type"] not in self.MATCH_EVENTS:
            return None

        event["type"] = self.MATCH_EVENTS[event["type"]]
        event["time"] = event_html.css(".time-box, .time-box-wide").xpath('string(.)').extract()[0]
        if event["type"] == self.SUBSTITUTION_EVENT_TYPE:
            event["in"] = event_html.css(".substitution-in-name").xpath('string(.)').extract()[0]
            event["out"] = event_html.css(".substitution-out-name").xpath('string(.)').extract()[0]
            return event

        event["participant"] = event_html.css(".participant-name").xpath('string(.)').extract()[0]

        if len(event_html.css(".assist")) == 1:
            event["assist"] = event_html.css(".assist").xpath('string(.)').extract()[0]

        return event

    def parse_events(self, html, item):
        path = "//*[@id='parts']//td[contains(@class, 'summary-vertical')]/*[@class='wrapper']"
        events_list = html.xpath(path)
        print events_list

        events = []
        for event in events_list:
            info = self.parse_event(event)
            if info is not None:
                events.append(info)
        item['events'] = events

    """
    parse_individual_stat: Parses a single player statistics
    @param stat - Html element where the player information is contained
    @param headers [List] - Name of the individual statistics
    @return [List] [{
        "name": 'Name of the player',
        "team": 'Name of the team the player belongs to',
        "stats": 'Statistics of the player [Object]... "stat_name": "stat_val"'
    }]
    """
    def parse_individual_stat(self, stat, headers):
        player_name_path = "td.player-label a"
        team_abbr_path = "td.team-label"
        values_path = "td.value-col"

        # Field names
        name_field = "name"
        stats_field = "stats"
        team_field = "team"

        values = stat.css(values_path).xpath('string(.)').extract()
        player = {}
        player[name_field] = stat.css(player_name_path).xpath('string(.)').extract()[0]
        player[team_field] = stat.css(team_abbr_path).xpath('string(.)').extract()[0]

        player[stats_field] = {}
        for i, header in enumerate(headers):
            player[stats_field][header] = values[i]

        return player

    """
    parse_individual_stats: Parses player statistics
    @param html - Where the information is contained
    @param @ref item - Common item where the info is stored
    """
    def parse_individual_stats(self, html, item):
        path = "#tab-player-statistics-0-statistic tbody tr"
        headers_path = "#tab-player-statistics-0-statistic th.sortable-type-num"
        player_list = html.css(path)
        headers = html.css(headers_path).xpath('@title').extract()

        # Individual stats name translation
        for i, header in enumerate(headers):
            headers[i] = self.MATCH_INDIVIDUAL_STATS[header.encode('utf-8')]

        item["players"] = []
        for player in player_list:
            player_stat = self.parse_individual_stat(player, headers)
            if player_stat is not None:
                item["players"].append(player_stat)

    """
    parse_stat: Parses a single team statistic from a match
    @param stat - Html element where the information is contained
    @param away_stats - Where the away team stats will be stored
    @param local_stats - Where the local team stats will be stored as follows:{
        "ball_control": 58,
        "shots": 12,
        ...
    }
    """
    def parse_stat(self, stat, local_stats, away_stats):
        stat_name_path = "td.score.stats"
        home_stat_path = "td.fl > div:first-child"
        away_stat_path = "td.fr > div:last-child"

        stat_name = stat.css(stat_name_path).xpath('string(.)').extract()[0]
        try:
            # Translation of the name of the statistic
            stat_name = self.MATCH_STATS[stat_name.encode('utf-8')]
        except KeyError:
            return

        local_stats[stat_name] = stat.css(home_stat_path).xpath('string(.)').extract()[0]
        away_stats[stat_name] = stat.css(away_stat_path).xpath('string(.)').extract()[0]

    """
    parse_stats: Parses team statistics from a match
    @param html - Where the information is contained
    @param @ref item - Common item where the info is stored
    in the item, the [Dict] objects local_stats and away_stats will be stored
    """
    def parse_stats(self, html, item):
        path = "#tab-statistics-0-statistic tr"
        stats_list = html.css(path)

        local_stats = {}
        away_stats = {}
        for stat in stats_list:
            self.parse_stat(stat, local_stats, away_stats)

        item["local"] = local_stats
        item["away"] = away_stats

    """
    parse_result: Parses basic info of a match
    @param html - Where the information is contained
    @param @ref item - Common item where the info is stored
    """
    def parse_result(self, html, item):
        local_team_name = ".tname-home a"
        away_team_name = ".tname-away a"
        score_path = "#event_detail_current_result span.scoreboard"
        date_path = "#utime"
        competition_day_path = "#detcon > table a"

        date = html.css(date_path).xpath('string(.)').extract()[0]
        competition_day = html.css(competition_day_path).xpath('string(.)').extract()[0]

        item["team_home"] = html.css(local_team_name).xpath('string(.)').extract()[0]
        item["team_away"] = html.css(away_team_name).xpath('string(.)').extract()[0]
        item["goals_home"] = html.css(score_path)[0].xpath('string(.)').extract()[0]
        item["goals_away"] = html.css(score_path)[1].xpath('string(.)').extract()[0]
        if len(competition_day.split(" - ")) > 1:
            item["competition_day"] = competition_day.split(" - ")[1]
        item["date"] = date.split(" ")[0]
        item["time"] = date.split(" ")[1]

    def parse_match(self, response):
        self.driver.get(response.url)
        item = SportStatsItem()
        item["season"] = response.request.meta["season"]

        delay = 10
        try:
            WebDriverWait(self.driver, delay).until(EC.presence_of_element_located((By.ID, 'parts')))
            # Create HtmlResponse object from driver current HTML
            html = scrapy.http.HtmlResponse(url=response.url, body=self.driver.page_source, encoding='utf-8')
            self.parse_result(html, item)
            self.parse_events(html, item)
            if len(self.driver.find_elements_by_id("a-match-statistics")) > 0:
                self.driver.get(response.url + "#estadisticas-del-partido;0")
                WebDriverWait(self.driver, delay).until(EC.presence_of_element_located((By.ID, 'tab-statistics-0-statistic')))
                html = scrapy.http.HtmlResponse(url=response.url, body=self.driver.page_source, encoding='utf-8')
                self.parse_stats(html, item)

            if len(self.driver.find_elements_by_id("a-match-player-statistics")) > 0:
                self.driver.get(response.url + "#player-statistics;0")
                WebDriverWait(self.driver, delay).until(EC.presence_of_element_located((By.ID, 'tab-player-statistics-0-statistic')))
                html = scrapy.http.HtmlResponse(url=response.url, body=self.driver.page_source, encoding='utf-8')
                self.parse_individual_stats(html, item)
        except TimeoutException:
            print "Loading took too much time!"

        print item
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
            season = response.url.split("/")[-3]
            yield scrapy.Request(url=url, callback=self.parse_match, meta={"season": season})

    def parse_league(self, response):
        year_links = "//*[@id='tournament-page-archiv']//td[1]/a/@href"
        resources = response.xpath(year_links).extract()
        print resources

        for resource in resources:
            url = self.base_url + resource + "resultados"
            print resource
            yield scrapy.Request(url=url, callback=self.parse_season)
