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
                    tempdata.append({i:data[i]["last"]})
            return tempdata
        else:
            if "last" in data:
                return data["last"]

    def api_query(self, command, params={}):

        default_params = {
            'nonce': int(dt.datetime.now().timestamp()),
            'command': command
        }
        params.update(default_params)

        # Trading / Private API Requests
        if command in self.__PRIVATE_COMMANDS:
            if self.__config is None:
                print('Specify API-Key and Secret first.')
                return

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
            print('API command does not exist!')