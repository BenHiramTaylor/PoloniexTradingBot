import datetime as dt
import hashlib
import hmac
import os
import time
import urllib.parse

import pandas as pd
import requests
from loguru import logger

from app.api.exceptions import PoloniexError
from app.config import PoloniexConfig


class Poloniex:
    def __init__(self, config: PoloniexConfig):

        self.__config = {"api_key": config.api_key, "api_secret": config.api_secret}
        self.__private_url = "https://poloniex.com/tradingApi"
        self.__public_url = "https://poloniex.com/public"
        self.__public_commands = config.public_commands
        self.__private_commands = config.private_commands
        self.__intervals = config.intervals
        self.__tickers = config.tickers
        self.__currencies = config.currencies

    def auto_create_df(self, ticker, interval, full_df=False):
        skip_loop = False

        if interval not in self.__intervals:
            intvls = "\n".join([str(i) for i in self.__intervals])
            raise PoloniexError(
                f"Invalid Interval.\nPlease use one of the following:\n{intvls}"
            )

        if ticker not in self.__tickers:

            tickers = "\n".join(self.__tickers)
            raise PoloniexError(
                f"Invalid Ticker.\nPlease use one of the following:\n{tickers}"
            )

        if not full_df:
            if interval == 300:
                start = dt.datetime.now() - dt.timedelta(weeks=14)
            elif interval == 900:
                start = dt.datetime.now() - dt.timedelta(weeks=42)
            elif interval == 1800:
                start = dt.datetime.now() - dt.timedelta(weeks=84)
            else:
                start = dt.datetime(2018, 1, 1)
            df = self.create_df(ticker, interval, start)
        else:
            _start = dt.datetime.now().timestamp()
            if interval == 300:
                weeks = 14
            elif interval == 900:
                weeks = 42
            elif interval == 1800:
                weeks = 84
            else:
                weeks = False
                skip_loop = True
            if not skip_loop:
                start = dt.datetime(2018, 1, 1)
                end = start + dt.timedelta(weeks=weeks)
                df = pd.DataFrame()
                while True:
                    final = False
                    if end > dt.datetime.now():
                        final = True
                        end = dt.datetime.now()
                    temp_df = self.create_df(ticker, interval, start, end=end)
                    start = end + dt.timedelta(seconds=interval)
                    end = start + dt.timedelta(weeks=weeks)
                    df = df.append(temp_df)
                    if final:
                        df = (
                            df.reset_index()
                            .drop_duplicates(subset="period", keep="first")
                            .set_index("period")
                        )
                        run_time = dt.datetime.now().timestamp() - _start
                        logger.info(f"Took {run_time} seconds to load full DF.")
                        break
            else:
                start = dt.datetime(2018, 1, 1)
                df = self.create_df(ticker, interval, start)
        return df

    def create_df(self, ticker, interval, start, end=None):
        if interval not in self.__intervals:
            intvls = "\n".join([str(i) for i in self.__intervals])
            raise PoloniexError(
                f"Invalid Interval.\nPlease use one of the following:\n{intvls}"
            )
        if ticker not in self.__tickers:
            tickers = "\n".join(self.__tickers)
            raise PoloniexError(
                f"Invalid Ticker.\nPlease use one of the following:\n{tickers}"
            )

        start = start.timestamp()
        if end is None:
            end = dt.datetime.now()
        end = end.timestamp()
        params = {
            "currencyPair": ticker,
            "start": str(start),
            "end": str(end),
            "period": interval,
        }

        result = self.api_query("returnChartData", params)
        if "error" in result:
            raise PoloniexError(result)

        data = []
        for i in result:

            tempdic = {}

            for key in i:
                if key == "date":
                    dtobj = dt.datetime.fromtimestamp(i[key])
                    tempdic["period"] = dt.datetime.strftime(dtobj, "%Y-%m-%d %H:%M:%S")

                else:
                    tempdic[key] = i[key]

            data.append(tempdic)

        df = pd.DataFrame(data)
        df.set_index("period", inplace=True)
        return df

    def load_df_from_json(self, file_path):
        if not os.path.exists(file_path):
            raise PoloniexError(
                "File path does not exist, should not be trying to load DF."
            )
        df = pd.read_json(file_path, orient="index", convert_dates=False)
        df.index.name = "period"
        df.index = df.index.astype(str)
        return df

    def get_current_ticker_data(self, ticker="All"):
        if ticker not in self.__tickers:
            if ticker != "All":
                tickers = "\n".join(self.__tickers)
                raise PoloniexError(
                    "Invalid Ticker.\nPlease use one of the"
                    f" following:\n{tickers}\nDefault is 'All'"
                )

        alltickers = self.api_query("returnTicker")

        if ticker == "All":
            return alltickers
        else:
            return alltickers[ticker]

    def get_current_price(self, ticker: str = "All"):
        data = self.get_current_ticker_data(ticker)
        if ticker == "All":

            tempdata = []
            for i in data:
                if "last" in data[i]:
                    tempdata.append({i: float(data[i]["last"])})

            return tempdata
        else:
            if "last" in data:
                return float(data["last"])

    def get_balance(self, currency) -> float:
        val = float(self.api_query("returnBalances")[currency])
        return val

    def get_1_percent_of_bal(self, currency):
        if currency not in self.__currencies:
            currencies = "\n".join(self.__currencies)
            raise PoloniexError(
                f"Invalid Currency.\nPlease use one of the following:\n{currencies}"
            )

        val = float(self.api_query("returnBalances")[currency])

        if val == 0:
            raise PoloniexError(
                "Your Balance is 0. Please deposit and restart the bot."
            )

        return val / 100

    def get_1_percent_trade_size(self, ticker, currency):

        if ticker not in self.__tickers:
            tickers = "\n".join(self.__tickers)
            raise PoloniexError(
                f"Invalid Ticker.\nPlease use one of the following:\n{tickers}"
            )

        if currency not in self.__currencies:
            currencies = "\n".join(self.__currencies)
            raise PoloniexError(
                f"Invalid Currency.\nPlease use one of the following:\n{currencies}"
            )

        one_percent = self.get_1_percent_of_bal(
            currency,
        )

        current_price = self.get_current_price(ticker)
        return one_percent / current_price

    def load_all_open_positions(self):
        data = {}
        params = {"currencyPair": "all"}
        open_positions = self.api_query("returnOpenOrders", params=params)
        for k in open_positions:
            if len(open_positions[k]):
                data[k] = open_positions[k]
        return data

    def api_query(self, command, params=None):

        if params is None:
            params = {}

        default_params = {
            "nonce": int(dt.datetime.now().timestamp()),
            "command": command,
        }
        params.update(default_params)

        # Trading / Private API Requests
        if command in self.__private_commands:
            if self.__config is None:
                raise PoloniexError("Specify api_key and api_secret first.")

            # Sign POST data for authentication
            params_encoded = urllib.parse.urlencode(params).encode("ascii")
            sign = hmac.new(
                self.__config["api_secret"].encode("ascii"),
                params_encoded,
                hashlib.sha512,
            ).hexdigest()
            headers = {"Key": self.__config["api_key"], "Sign": sign}
            while True:
                r = requests.post(self.__private_url, data=params, headers=headers)
                if r.status_code != 200:
                    logger.warning(f"Hit Rate limit. Sleeping for 3 Second. {r.text}")
                    time.sleep(3)
                    params["nonce"] = int(dt.datetime.now().timestamp())
                else:
                    break

            return r.json()

        # Trading / Public API Requests
        elif command in self.__public_commands:
            params.pop("nonce")
            if command == "returnMarketTradeHistory":
                params["command"] = "returnTradeHistory"
            while True:
                r = requests.get(self.__public_url, params)
                if r.status_code != 200:
                    time.sleep(0.5)
                else:
                    break
            return r.json()

        else:
            commands = []
            for i in self.__private_commands:
                commands.append(i)
            for i in self.__public_commands:
                commands.append(i)
            commands_list = "\n".join(commands)
            raise PoloniexError(
                "API command does not exist!\nPlease use one of the"
                f" following\n{commands_list}"
            )


__all__ = ["Poloniex"]
