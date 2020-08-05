from Poloniex import Errors
import datetime as dt
import requests

def check_ticker(Ticker):
    AllTickers = ["USDT_BTC"]
    if Ticker not in AllTickers:
        ReceivedTickers = '\n'.join(AllTickers)
        return Errors.TickerError(f"Ticker: {Ticker} is not in the list of received tickers, please use one of the following:\n{ReceivedTickers}")
    else:
        return False

def check_interval(Interval):
    AllowedIntervals = [300,900,1800,7200,14400,86400]
    if Interval not in AllowedIntervals:
        Intervals = ' '.join(AllowedIntervals)
        return Errors.IntervalError(f"Interval Invalid, needs to be one of the following: {Intervals}")
    else:
        return False

def get_current_price(Ticker=False, AllTickers=False):
    if (not Ticker and not AllTickers):
        return Errors.TickerError("Both Ticker and AllTickers cannot be False, please provide a value for one.")
    if Ticker:
        TickerCheck = check_ticker(Ticker)
        if TickerCheck:
            return TickerCheck

    r = requests.get("https://poloniex.com/public?command=returnTicker")
    if r.status_code != 200:
        return requests.HTTPError(f"Didn't get 200 status code on get_current_price, Got: {r.status_code}\n{r.text}")
    AllTickers = r.json()

    if AllTickers:
        return AllTickers
    else:
        return AllTickers[Ticker]

def all_close_data_json(Interval, Ticker, StartDate):
    IntervalCheck = check_interval(Interval)
    if IntervalCheck:
        return IntervalCheck

    closedata = []
    startunix = dt.datetime.strptime(StartDate, "%Y-%m-%d").timestamp()
    endunix = (dt.datetime.now()-dt.timedelta(days=1)).timestamp()

    rawdata = load_chart_data(Interval, Ticker, startunix, endunix)
    for i in rawdata:
        dtobj = dt.datetime.fromtimestamp(i['date'])
        closedata.append({
            "date":dt.datetime.strftime(dtobj,"%Y-%m-%d"),
            "close":i["close"]
        })

    return closedata

def load_chart_data(Interval, Ticker, StartUnix, EndUnix):
    IntervalCheck = check_interval(Interval)
    if IntervalCheck:
        return IntervalCheck

    params = {"currencyPair":Ticker, "period":Interval, "start":StartUnix, "end":EndUnix}
    url = 'https://poloniex.com/public?command=returnChartData'
    r = requests.get(url,params=params)
    if r.status_code != 200:
        return requests.HTTPError(f"Didn't get 200 status code on load_chart_data, Got: {r.status_code}\n{r.text}")
    result = r.json()
    return result