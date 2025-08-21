from util import get_list


def generator(name):
    with open(name + ".html", "w") as f:
        HEAD = f"""
            <html xmlns="http://www.w3.org/1999/xhtml">
            <head>
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
            <title>{name.upper()}</title>
            </head>
            <body >"""
        END = "</body> </html>"

        print(f"Generating HTML of {name.upper()} ...")
        body = ""
        for sid, title in get_list(name):
            if "-" in sid:
                body += "<hr width='95%' color='red'><hr width='95%' color='red'>"
                continue

            body += f"<p align=center>{sid}, {title}\n"
            body += f"<a href='https://www.cnyes.com/twstock/{sid}'>CNYES </a>"
            body += f"<a href='https://statementdog.com/analysis/{sid}'>財報狗 </a>"
            body += f"<a href='https://www.wantgoo.com/stock/{sid}'>玩股網 </a>"
            body += f"<a href='https://goodinfo.tw/StockInfo/StockDetail.asp?STOCK_ID={sid}'>Goodinfo </a>"
            body += f"<a href='https://histock.tw/stock/{sid}'>HiStock </a>"
            body += f"<a href='https://www.fugle.tw/ai/{sid}'>Fugle </a>"
            body += f"<a href='www/{sid}.html'> Report</a>"
            body += f"<img src='pic/{sid}.png' width='80%' class='center'/></p>\n"

        f.write(HEAD + body + END)


def html_generator():
    generator("tse")
    # generator("otc")
    # generator("filter")


if __name__ == "__main__":
    html_generator()
