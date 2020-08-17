import requests
import datetime as dt
import pandas as pd
import json
import hmac
import hashlib

class PoloniexError(Exception):
    """Base Exception for handling Poloniex API Errors"""
    pass

class Poloniex:
    def __init__(self,API_KEY, API_SECRET):
        self.API_KEY = API_KEY
        self.API_SECRET = API_SECRET
        self.PRIVATE_URL = "https://poloniex.com/tradingApi"
        self.PUBLIC_URL = "https://poloniex.com/public"
        with open("PoloniexSettings.json","r")as f:
            settings = json.load(f)
        self.INTERVALS = settings["Intervals"]
        self.TICKERS = settings["Tickers"]

    def private_post(self,command):
        nonce = int(dt.datetime.now().timestamp())
        params = {"command":command,"nonce":nonce}
        signature = hmac.new(str.encode(self.API_SECRET, 'utf-8'),str.encode(f'command={command}&nonce={str(nonce)}', 'utf-8'),hashlib.sha512)
        headers = {"Key":self.API_KEY,"Sign":signature.hexdigest()}
        return headers, params
    
    def public_post(self,params):
        while True:
            r = requests.get(self.PUBLIC_URL,params=params)
            if r.status_code == 200:
                break
            else:
                print(f"Got Status Code: {r.status_code}, trying again.")
        return r.json()
    
    def create_df(self,ticker,interval,start=None):
        if interval not in self.INTERVALS:
            intvls = '\n'.join(self.INTERVALS)
            raise PoloniexError(f"Invalid Interval.\nPlease use one of the following:\n{intvls}")
        if ticker not in self.TICKERS:
            tickers = '\n'.join(self.TICKERS)
            raise PoloniexError(f"Invalid Ticker.\nPlease use one of the following:\n{tickers}")
        if not start:
            start = dt.datetime(2018,1,1).timestamp()
            
        end = (dt.datetime.now()-dt.timedelta(days=1)).timestamp()
        params = {
            "command":"returnChartData",
            "currencyPair":ticker,
            "start":str(start),
            "end":str(end),
            "period":interval
            }

        result = self.public_post(params)
        data = []
        for i in result:
            tempdic = {}
            for key in i:
                if key == "date":
                    dtobj = dt.datetime.fromtimestamp(i[key])
                    tempdic['ts'] = dt.datetime.strftime(dtobj,"%Y-%m-%d")
                else:
                    tempdic[key] = i[key]
            data.append(tempdic)

        df = pd.DataFrame(data)
        df.set_index("ts",inplace=True)
        return df
