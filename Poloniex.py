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
        self.PRIVATE_COMMANDS = settings["Private_Commands"]
        self.INTERVALS = settings["Intervals"]
        self.TICKERS = settings["Tickers"]

    def private_auth(self,command):
        nonce = int(dt.datetime.now().timestamp())
        params = {"command":command,"nonce":nonce}
        signature = hmac.new(str.encode(self.API_SECRET, 'utf-8'),str.encode(f'command={command}&nonce={str(nonce)}', 'utf-8'),hashlib.sha512)
        headers = {"Key":self.API_KEY,"Sign":signature.hexdigest()}
        return headers, params
    
    def execute_command(self,command):
        if command in self.PUBLIC_COMMANDS:
            url = self.PUBLIC_URL
        elif command in self.PRIVATE_COMMANDS:
            url = self.PRIVATE_URL
        else:
            return PoloniexError("Command not recognised.")

        headers, params = self.private_auth(command)
        r = requests.get(url, headers=headers,params=params)
        if r.status_code != 200:
            print(f"Did not get 200 on {command}, got: {r.status_code}\n{r.text}")
        result = r.json()
        return result