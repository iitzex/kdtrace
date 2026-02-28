import time
import json
import requests
import pandas as pd
from typing import Dict, Any
from util import get_list

RELOAD = False

headers = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'zh-TW,zh;q=0.7',
    'dnt': '1',
    'origin': 'https://www.cnyes.com',
    'priority': 'u=1, i',
    'referer': 'https://www.cnyes.com/',
    'sec-ch-ua': '"Not;A=Brand";v="99", "Brave";v="139", "Chromium";v="139"',
    'sec-ch-ua-mobile': '?1',
    'sec-ch-ua-platform': '"Android"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'sec-gpc': '1',
    'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
    'x-platform': 'WEB',
    'x-system-kind': 'LOBBY',
}

ts = int(time.time()) - 31536000 * 5
params = {
    'year': '5',
    'to': f'{ts}',
}
params_eps = {
    'resolution': 'Q',
    'year': '5',
    'to': f'{ts}',
}


def fetch_json(sid: str, url: str, params: Dict[str, Any], filename: str) -> Dict[str, Any]:
    if RELOAD:
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    else:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)

    return data["data"][0]


def get_revenue(sid: str) -> pd.DataFrame:
    try:
        url = f'https://marketinfo.api.cnyes.com/mi/api/v1/financialIndicator/revenue/TWS:{sid}:STOCK'
        filename = f"json/{sid}_revenue.json"
        stock_data = fetch_json(sid, url, params, filename)
        df_revenue = pd.DataFrame({
            "revenue": stock_data["revenue"],
            "revenueYOY": stock_data["revenueYOY"]
        }, index=pd.to_datetime(stock_data["time"], unit="s"))
        df_revenue.index.name = "date"
        return df_revenue
    except Exception as e:
        print(f"Error fetching revenue data for {sid}: {e}")
        return pd.DataFrame()


def get_profitability(sid: str) -> pd.DataFrame:
    try:
        url = f'https://marketinfo.api.cnyes.com/mi/api/v1/financialIndicator/profitability/TWS:{sid}:STOCK'
        filename = f"json/{sid}_profitability.json"
        stock_data = fetch_json(sid, url, params, filename)
        df_profitability = pd.DataFrame({
            "grossMargin": stock_data["grossMargin"],
            "operatingMargin": stock_data["operatingMargin"],
            "profitMargin": stock_data["profitMargin"],
        }, index=pd.to_datetime(stock_data["time"], unit="s"))
        df_profitability.index.name = "date"
        return df_profitability
    except Exception as e:
        print(f"Error fetching profitability data for {sid}: {e}")
        return pd.DataFrame()


def get_eps(sid: str) -> pd.DataFrame:
    try:
        url = f'https://marketinfo.api.cnyes.com/mi/api/v1/financialIndicator/eps/TWS:{sid}:STOCK'
        filename = f"json/{sid}_eps.json"
        stock_data = fetch_json(sid, url, params_eps, filename)
        df_eps = pd.DataFrame({
            "eps": stock_data["eps"],
            "epsYOY": stock_data["epsYOY"],
        }, index=pd.to_datetime(stock_data["time"], unit="s"))
        df_eps.index.name = "date"
        return df_eps
    except Exception as e:
        print(f"Error fetching EPS data for {sid}: {e}")
        return pd.DataFrame()


def get_investors(sid: str) -> pd.DataFrame:
    try:
        url = f'https://marketinfo.api.cnyes.com/mi/api/v1/chipsObserve/3majorInvestors/TWS:{sid}:STOCK'
        filename = f"json/{sid}_investors.json"
        stock_data = fetch_json(sid, url, params, filename)

        df_investors = pd.DataFrame(
            [{"foreign": i['foreignVolume'], "domestic": i['domesticVolume'],
              "dealer": i['dealerVolume'], "total": i['totalVolume']}
             for i in stock_data["volumeCharting"]],
            index=pd.to_datetime(stock_data["time"], unit="s"),
        )
        df_investors.index.name = "date"

        return df_investors
    except Exception as e:
        print(f"Error fetching investors data for {sid}: {e}")
        return pd.DataFrame()


if RELOAD:
    print("\t+")
else:
    print("\t-")

if __name__ == "__main__":
    RELOAD = True
    # sid = "2330"  # Example stock ID
    # print(get_revenue(sid))
    # print(get_eps(sid))
    # print(get_profitability(sid))
    # df = get_investors(sid)
    # print(df)

    for sid, name in get_list("tse"):
        print(sid)
        df = get_investors(sid)
        # print(df)
