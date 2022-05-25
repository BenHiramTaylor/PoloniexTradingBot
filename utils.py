import yaml
from app.config import Config
from ccxt.poloniex import poloniex


def load_config(path: str) -> Config:

    try:

        with open(file=path, mode="r", encoding="utf-8") as fh:
            return Config(**yaml.safe_load(fh))

    except (yaml.YAMLError, FileNotFoundError) as exc:
        print(exc)


def get_balance(client: poloniex, currency) -> float:
    balance = client.fetch_balance()[currency]
    return balance["free"]


def get_current_price(client: poloniex, ticker: str) -> float:
    ticker_info = client.fetch_ticker(symbol=ticker)
    return ticker_info["last"]


def get_1_percent_trade_size(client: poloniex, ticker, currency) -> float:

    balance = get_balance(client=client, currency=currency)
    one_percent: float = balance / 100
    current_price = get_current_price(client=client, ticker=ticker)
    return one_percent / current_price


__all__ = [
    "load_config",
    "get_1_percent_trade_size",
    "get_balance",
    "get_current_price",
]
