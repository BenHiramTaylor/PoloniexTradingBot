from pydantic import BaseSettings


class PoloniexConfig(BaseSettings):
    api_key: str
    api_secret: str
    public_commands: list[str]
    private_commands: list[str]
    tickers: list[str]
    intervals: list[int]
    currencies: list[str]


class Config(BaseSettings):
    poloniex: PoloniexConfig
    interval: int = 7200
    ticker: str = "USDT_ETH"
    auto_trade: bool = True


__all__ = ["Config", "PoloniexConfig"]