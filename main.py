import datetime as dt
import json
import requests
import os

def GetCurrentPrice(Ticker, AllTickers=False):
    r = requests.get("https://poloniex.com/public?command=returnTicker")
    if r.status_code != 200:
        print(f"Didn't get 200 status code on GetCurrentPrice, Got: {r.status_code}")
        print(r.text)
        return

    result = r.json()

    if AllTickers:
        return result
    
    if Ticker not in result:
        ReceivedTickers = '\n'.join(result)
        print(f"Ticker: {Ticker} is not in the list of received tickers, please use one of the following: \n{ReceivedTickers}")
        return

    return result[Ticker]

def AllCloseDataJSON(Interval, Ticker,StartDate):
    if Interval not in AllowedIntervals:
        Intervals = ' '.join(AllowedIntervals)
        print(f"Interval Invalid, needs to be one of the following: {Intervals}")
        return

    closedata = []
    startunix = dt.datetime.strptime(StartDate, "%Y-%m-%d").timestamp()
    endunix = (dt.datetime.now()-dt.timedelta(days=1)).timestamp()

    rawdata = LoadChartData(Interval, Ticker, startunix, endunix)
    for i in rawdata:
        dtobj = dt.datetime.fromtimestamp(i['date'])
        closedata.append({
            "date":dt.datetime.strftime(dtobj,"%Y-%m-%d"),
            "close":i["close"]
        })

    return closedata

def LoadChartData(Interval,Ticker,StartUnix,EndUnix):
    if Interval not in AllowedIntervals:
        Intervals = ' '.join(AllowedIntervals)
        print(f"Interval Invalid, needs to be one of the following: {Intervals}")
        return
    params = {"currencyPair":Ticker, "period":Interval, "start":StartUnix, "end":EndUnix}
    url = 'https://poloniex.com/public?command=returnChartData'
    r = requests.get(url,params=params)
    if r.status_code != 200:
        print(f"Didn't get 200 status code on LoadChartData, Got: {r.status_code}")
        print(r.text)
        return
    result = r.json()
    return result

if __name__ == "__main__":
    AllowedIntervals = [300,900,1800,7200,14400,86400]
