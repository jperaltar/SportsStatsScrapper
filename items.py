# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class SportStatsItem(scrapy.Item):
    # define the fields for your item here like:
    time = scrapy.Field()
    team_home = scrapy.Field()
    team_away = scrapy.Field()
    score = scrapy.Field()
    extra = scrapy.Field()
