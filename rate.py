import subprocess
import pandas as pd
from util import get_list


def curl():
    r = subprocess.check_output(
        ["curl", "-X", "GET", "https://stock.wespai.com/rate114"]
    )
    text = r.decode("UTF-8", errors="backslashreplace")

    with open("rate.html", "w") as f:
        f.write(text)


def read_html():
    curl()
    with open("rate.html", "r") as f:
        frame = pd.read_html(f.read(), index_col="代號")

    df = frame[0][["公司", "現金殖利率", "股價", "配息", "除息日", "發息日"]]
    df.loc[:, "配息"] *= 1000
    return df


if __name__ == "__main__":
    df = read_html()

    my = [code for code, _ in get_list("my")]
    df_my = df.loc[my]

    f = pd.ExcelWriter("rate.xlsx")
    df_my.to_excel(f, "My")
    df.to_excel(f, "All")
    f.save()

    subprocess.run(["open", "rate.xlsx"])
