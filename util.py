import json
import os
import csv
from os import listdir
from os.path import isfile, join


def add_columns():
    # add columns for data/csv
    mypath = "data/"
    onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]

    for filename in onlyfiles:
        with open("data/" + filename, "r") as original:
            lines = original.readlines()

        new_lines = []
        for line in lines:
            if "--" not in line:
                new_lines.append(line)

        with open("data/" + filename, "w") as modified:
            modified.writelines(new_lines)


def convert_time():
    all = os.listdir("data/")
    for _ in all:
        with open("data/" + _, "r") as fp:
            tp = open("old/" + _, "w")
            for i, line in enumerate(fp.readlines()):
                if i == 0:
                    tp.write(line.__str__())
                    continue
                time = line.split(",")
                s = time[0].split("/")
                s[0] = str(int(s[0]) + 1911)
                t = "-".join(s)
                time[0] = t
                tp.write(",".join(time))


def get_list(name, bound=0):
    f = open(name + ".csv", "r")

    r = []
    for stock in csv.reader(f):
        sid = stock[0]
        title = (stock[1]).strip()

        if int(sid) >= int(bound):
            # yield sid, title
            r.append((sid, title))

    f.close()
    return r


if __name__ == "__main__":
    r = get_list("tse")
    for sid, title in r:
        print(sid, title)
        try:
            with open(f"json/{sid}_eps.json", "r", encoding="utf-8") as f:
                data = json.load(f)
        except OSError as e:
            print(e)

            import fetch
            fetch.RELOAD = True

            df = fetch.get_revenue(sid)
            df = fetch.get_eps(sid)
            df = fetch.get_profitability(sid)
            print(f"loading {sid}")
