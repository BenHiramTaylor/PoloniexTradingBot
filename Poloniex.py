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
        self.PUBLIC_COMMANDS = []
        self.PRIVATE_COMMANDS = []
        self.INTERVALS = []
        with open("PoloniexSettings.json","r")as f:
            settings = json.load(f)
        self.PUBLIC_COMMANDS = settings["Public_Commands"]
        self.INTERVALS = settings["Intervals"]
        self.TICKERS = settings["Tickers"]

    def private_post(self,command):
        nonce = int(dt.datetime.now().timestamp())
        params = {"command":command,"nonce":nonce}
        signature = hmac.new(str.encode(self.API_SECRET, 'utf-8'),str.encode(f'command={command}&nonce={str(nonce)}', 'utf-8'),hashlib.sha512)
        headers = {"Key":self.API_KEY,"Sign":signature.hexdigest()}
        return headers, params
    
    def public_post(self,command):
        if command not in self.PUBLIC_COMMANDS:
            return PoloniexError("Command not recognised.")
        if command == "marketTradeHistory":
            command = "returnTradeHistory"
        while True:
            r = requests.get(self.PUBLIC_URL,params={"command":command})
            if r.status_code == 200:
                break
            else:
                print(f"Got Status Code: {r.status_code}, trying again.")
        return r.json()
