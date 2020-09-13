import requests
import datetime as dt
import pandas as pd
import json
import hmac
import hashlib
import urllib.parse
import time

class PoloniexError(Exception):
    """Base Exception for handling Poloniex API Errors"""
    pass

class Poloniex:
    def __init__(self,API_KEY, API_SECRET):
        self.__config = {
            "API_KEY": API_KEY,
            "Secret": API_SECRET
        }
        self.__PRIVATE_URL = "https://poloniex.com/tradingApi"
        self.__PUBLIC_URL = "https://poloniex.com/public"
        with open("PoloniexSettings.json","r")as f:
            settings = json.load(f)
        self.__PUBLIC_COMMANDS = settings["Public_Commands"]
        self.__PRIVATE_COMMANDS = settings["Private_Commands"]
        self.__INTERVALS = settings["Intervals"]
        self.__TICKERS = settings["Tickers"]
        self.__CURRENCIES = settings["Currencies"]

    def auto_create_df(self,ticker,interval):
        if interval not in self.__INTERVALS:
            intvls = '\n'.join(self.__INTERVALS)
            raise PoloniexError(f"Invalid Interval.\nPlease use one of the following:\n{intvls}")
        if ticker not in self.__TICKERS:
            tickers = '\n'.join(self.__TICKERS)
            raise PoloniexError(f"Invalid Ticker.\nPlease use one of the following:\n{tickers}")
        if interval == 300:
            start = dt.datetime.now()-dt.timedelta(weeks=14)
        elif interval == 900:
            start = dt.datetime.now()-dt.timedelta(weeks=42)
        elif interval == 1800:
            start = dt.datetime.now()-dt.timedelta(weeks=84)
        else:
            start = dt.datetime(2018,1,1)
        
        df = self.create_df(ticker,interval,start)
        return df
    
    def create_df(self,ticker,interval,start,end=None):
        if interval not in self.__INTERVALS:
            intvls = '\n'.join(self.__INTERVALS)
            raise PoloniexError(f"Invalid Interval.\nPlease use one of the following:\n{intvls}")
        if ticker not in self.__TICKERS:
            tickers = '\n'.join(self.__TICKERS)
            raise PoloniexError(f"Invalid Ticker.\nPlease use one of the following:\n{tickers}")

        start = start.timestamp()
        if end is None:
            end = dt.datetime.now()
        end = end.timestamp()
        params = {
            "currencyPair":ticker,
            "start":str(start),
            "end":str(end),
            "period":interval
            }

        result = self.api_query("returnChartData",params)
        if "error" in result:
            raise PoloniexError(result)
        
        data = []
        for i in result:
            tempdic = {}
            for key in i:
                if key == "date":
                    dtobj = dt.datetime.fromtimestamp(i[key])
                    tempdic['ts'] = dt.datetime.strftime(dtobj,"%Y-%m-%d %H:%M:%S")
                else:
                    tempdic[key] = i[key]
            data.append(tempdic)

        df = pd.DataFrame(data)
        df.set_index("ts",inplace=True)
        return df
    
    def get_current_ticker_data(self,Ticker="All"):
        if Ticker not in self.__TICKERS:
            if Ticker != "All":
                tickers = '\n'.join(self.__TICKERS)
                raise PoloniexError(f"Invalid Ticker.\nPlease use one of the following:\n{tickers}\nDefault is 'All'")

        AllTickers = self.api_query("returnTicker")

        if Ticker == "All":
            return AllTickers
        else:
            return AllTickers[Ticker]
    
    def get_current_price(self,Ticker="All"):
        data = self.get_current_ticker_data(Ticker)
        if Ticker == "All":
            tempdata = []
            for i in data:
                if "last" in data[i]:
                    tempdata.append({i:float(data[i]["last"])})
            return tempdata
        else:
            if "last" in data:
                return float(data["last"])
    
    def get_1_percent_of_bal(self,Currency):
        if Currency not in self.__CURRENCIES:
            currencies = '\n'.join(self.__CURRENCIES)
            raise PoloniexError(f"Invalid Currency.\nPlease use one of the following:\n{currencies}")

        val = float(self.api_query("returnBalances")[Currency])
        if val == 0:
            raise PoloniexError("Your Balance is 0. Please deposit and restart the bot.")
        return val / 100
    
    def get_1_percent_trade_size(self, Ticker, Currency):
        if Ticker not in self.__TICKERS:
            tickers = '\n'.join(self.__TICKERS)
            raise PoloniexError(f"Invalid Ticker.\nPlease use one of the following:\n{tickers}")
        if Currency not in self.__CURRENCIES:
            currencies = '\n'.join(self.__CURRENCIES)
            raise PoloniexError(f"Invalid Currency.\nPlease use one of the following:\n{currencies}")
        one_percent = self.get_1_percent_of_bal(Currency)
        current_price = self.get_current_price(Ticker)
        return one_percent / current_price

    def load_all_open_positions(self):
        data = {}
        open_positions = self.api_query("returnOpenOrders",{"currencyPair":"all"})
        for k in open_positions:
            if len(open_positions[k]):
                data[k] = open_positions[k]
        return data

    def api_query(self, command, params={}):

        default_params = {
            'nonce': int(dt.datetime.now().timestamp()),
            'command': command
        }
        params.update(default_params)

        # Trading / Private API Requests
        if command in self.__PRIVATE_COMMANDS:
            if self.__config is None:
                raise PoloniexError('Specify API-Key and Secret first.')

            # Sign POST data for authentication
            params_encoded = urllib.parse.urlencode(params).encode('ascii')
            sign = hmac.new(self.__config['Secret'].encode('ascii'), params_encoded, hashlib.sha512).hexdigest()
            headers = {
                'Key': self.__config['API_KEY'],
                'Sign': sign
            }
            while True:
                r = requests.post(self.__PRIVATE_URL, data=params, headers=headers)
                if r.status_code != 200:
                    time.sleep(0.5)
                else:
                    break

            return r.json()

        # Trading / Public API Requests
        elif command in self.__PUBLIC_COMMANDS:
            params.pop('nonce')
            if command == 'returnMarketTradeHistory':
                params['command'] = 'returnTradeHistory'
            while True:
                r = requests.get(self.__PUBLIC_URL, params)
                if r.status_code != 200:
                    time.sleep(0.5)
                else:
                    break
            return r.json()

        else:
            Commands = []
            for i in self.__PRIVATE_COMMANDS:
                Commands.append(i)
            for i in self.__PUBLIC_COMMANDS:
                Commands.append(i)
            Commands_List = "\n".join(Commands)
            raise PoloniexError(f'API command does not exist!\nPlease use one of the following\n{Commands_List}')