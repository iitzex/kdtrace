import re
import requests
from bs4 import BeautifulSoup
from typing import List, Tuple


def get(addr: str) -> List[Tuple[str, str]]:
    try:
        r = requests.get(addr)
        print(f"HTTP {r.status_code}: {r.url}")
        content = r.content.decode('Big5-HKSCS', errors='backslashreplace')
        soup = BeautifulSoup(content, "lxml")
        stock: List[Tuple[str, str]] = []
        for row in soup.find_all('tr'):
            # Ensure 'row' is a Tag before calling find_all
            if not hasattr(row, 'find_all'):
                continue
            column = row.find_all('td')
            if len(column) < 5:
                continue
            if column[5].text == 'ESVUFR':
                match = re.search(r"(\d{4})(.*)", column[0].text)
                if match:
                    sid = match.group(1)
                    name = match.group(2).strip()
                    stock.append((sid, name))
        return stock
    except Exception as e:
        print(f"Error fetching or parsing: {e}")
        return []


def save(stock: List[Tuple[str, str]], cname: str) -> None:
    print(f"Writing {cname}.csv ...")
    with open(f'{cname}.csv', 'w', encoding='utf-8') as f:
        for sid, name in stock:
            f.write(f"{sid},{name}\n")


if __name__ == '__main__':
    tse_url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    tse = get(tse_url)
    if tse:
        save(tse, 'tse')
    # otc_url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"
    # otc = get(otc_url)
    # if otc:
    #     save(otc, 'otc')
