# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import datetime
import unicodecsv as csv
from sport_stats.items import SportStatsItem


class SportStatsPipeline(object):
    def __init__(self):
        name = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
        self.myCsv = csv.writer(open('log-' + name + '.csv', 'wb'))
        item = SportStatsItem()
        self.myCsv.writerow(list(item.fields.keys()))

    def process_item(self, item, spider):
        print item.keys()
        if len(item.keys()) == 0:
            return

        row = []
        for field in item.fields:
            try:
                row.append(item[field])
            except KeyError as e:
                row.append("")

        self.myCsv.writerow(row)
        return item
