# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class SportStatsItem(scrapy.Item):
    # define the fields for your item here like:
    date = scrapy.Field()
    time = scrapy.Field()
    team_home = scrapy.Field()
    team_away = scrapy.Field()
    goals_home = scrapy.Field()
    goals_away = scrapy.Field()
    local = scrapy.Field()
    away = scrapy.Field()
    players = scrapy.Field()
    events = scrapy.Field()
    season = scrapy.Field()
    competition_day = scrapy.Field()
