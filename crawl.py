import os
from os import mkdir
from os.path import isdir
import time
from time import mktime, strptime
import csv
import logging
from datetime import datetime, timedelta
import requests
import random


class Crawler:
    def __init__(self, prefix="data"):
        """ Make directory if not exist when initialize """
        if not isdir(prefix):
            mkdir(prefix)
        self.prefix = prefix

    def _clean_row(self, row):
        """ Clean comma and spaces """
        for index, content in enumerate(row):
            row[index] = content.replace(",", "")
        return row

    def _record(self, stock_id, row):
        """ Save row to csv file """
        f = open("{}/{}.csv".format(self.prefix, stock_id), "a")
        s = os.stat("{}/{}.csv".format(self.prefix, stock_id))

        if s.st_size == 0:
            f.write("date,amount,volume,open,high,low,close,diff,number\n")

        cw = csv.writer(f, lineterminator="\n")
        cw.writerow(row)
        f.close()

    def _get_tse_data(self, date_str):
        dstr = date_str.replace("-", "")
        url = f"https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date={dstr}&type=ALLBUT0999"

        try:
            page = requests.get(url)
            print(page.status_code, page.url)
            j = page.json()
            if j["stat"] != "OK":
                print(j["stat"])
                return

            for item in j['tables'][8]['data']:
                sign = "-" if "-" in item[9] else ""
                row = self._clean_row(
                    [
                        date_str,  # 日期
                        item[2][:-4],  # 成交股數
                        item[4],  # 成交金額
                        item[5],  # 開盤價
                        item[6],  # 最高價
                        item[7],  # 最低價
                        item[8],  # 收盤價
                        sign + item[10],  # 漲跌價差
                        item[3],  # 成交筆數
                    ]
                )

                self._record(item[0], row)
        except OSError as e:
            print(e)

    def _get_otc_data(self, date_str, date_str_tw):
        ts = int(mktime(strptime(f"{date_str}-12", "%Y-%m-%d-%H"))) * 100
        url = f"http://www.tpex.org.tw/web/stock/aftertrading/otc_quotes_no1430/stk_wn1430_result.php?l=zh-tw&d={date_str_tw}&sect=EW&_={ts}"
        page = requests.get(url)
        j = page.json()

        if j["iTotalRecords"] == 0:
            logging.error("Can not get OTC data at {}".format(date_str))
            return

        for item in j["aaData"]:
            row = self._clean_row(
                [
                    date_str,  # 日期
                    item[7][:-4],  # 成交股數
                    item[8],  # 成交金額
                    item[4],  # 開盤價
                    item[5],  # 最高價
                    item[6],  # 最低價
                    item[2],  # 收盤價
                    item[3],  # 漲跌價差
                    item[9],  # 成交筆數
                ]
            )

            self._record(item[0], row)

    def get_data(self, year, month, day):
        date_str = "{0}-{1:02d}-{2:02d}".format(year, month, day)
        # date_str_tw = '{0}/{1:02d}/{2:02d}'.format(year - 1911, month, day)

        print("Crawling {}".format(date_str))
        self._get_tse_data(date_str)
        # self._get_otc_data(date_str, date_str_tw)


def get():
    with open("data/0050.csv", "r") as f:
        last_line = f.readlines()[-1]
        last_day = last_line.split(",")[0]
        begin = datetime.strptime(last_day, "%Y-%m-%d")
        begin += timedelta(1)

    end = datetime.today()
    # end = begin + timedelta(2000)

    crawler = Crawler()

    print(f"BEGIN: {begin}")
    print(f"END: {end}")

    max_error = 5
    error = 0
    while error < max_error and end >= begin:
        try:
            crawler.get_data(begin.year, begin.month, begin.day)
            time.sleep(random.randint(1, 5))
            error = 0
        except OSError:
            logging.error(
                "Crawl raise error {} {} {}".format(
                    begin.year, begin.month, begin.day)
            )
            error += 1
            continue
        finally:
            begin += timedelta(1)


if __name__ == "__main__":
    get()
