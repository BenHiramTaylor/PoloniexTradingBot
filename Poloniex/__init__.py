from Poloniex.Errors import TickerError
from Poloniex import Errors
import datetime as dt
import json
import requests
import os

def check_ticker(Ticker):
    AllTickers = ['BTC_BTS','BTC_DASH', 'BTC_DOGE', 'BTC_LTC', 'BTC_NXT', 'BTC_STR', 'BTC_XEM', 'BTC_XMR', 'BTC_XRP', 'USDT_BTC', 'USDT_DASH', 'USDT_LTC', 'USDT_STR', 'USDT_XMR', 'USDT_XRP', 'BTC_ETH', 'USDT_ETH', 'BTC_SC', 'BTC_DCR', 'BTC_LSK', 'BTC_STEEM', 'BTC_ETC', 'ETH_ETC', 'USDT_ETC', 'BTC_REP', 'USDT_REP', 'BTC_ARDR', 'BTC_ZEC', 'ETH_ZEC', 'USDT_ZEC', 'BTC_STRAT', 'BTC_GNT', 'BTC_ZRX', 'ETH_ZRX', 'BTC_CVC', 'BTC_OMG', 'BTC_GAS', 'BTC_STORJ', 'BTC_EOS', 'ETH_EOS', 'USDT_EOS', 'BTC_SNT', 'BTC_KNC', 'BTC_BAT', 'ETH_BAT', 'USDT_BAT', 'BTC_LOOM', 'USDT_DOGE', 'USDT_GNT', 'USDT_LSK', 'USDT_SC', 'USDT_ZRX', 'BTC_QTUM', 'USDT_QTUM', 'USDC_BTC', 'USDC_ETH', 'USDC_USDT', 'BTC_MANA', 'USDT_MANA', 'BTC_BNT', 'BTC_BCHABC', 'USDC_BCHABC', 'BTC_BCHSV', 'USDC_BCHSV', 'USDC_XRP', 'USDC_XMR', 'USDC_STR', 'USDC_DOGE', 'USDC_LTC', 'USDC_ZEC', 'BTC_FOAM', 'BTC_NMR', 'BTC_POLY', 'BTC_LPT', 'USDC_GRIN', 'BTC_ATOM', 'USDC_ATOM', 'USDT_ATOM', 'USDC_DASH', 'USDC_EOS', 'USDC_ETC', 'USDT_BCHSV', 'USDT_BCHABC', 'USDT_GRIN', 'BTC_TRX', 'USDC_TRX', 'USDT_TRX', 'BTC_ETHBNT', 'TRX_ETH', 'TRX_XRP', 'USDT_BTT', 'TRX_BTT', 'USDT_WIN', 'TRX_WIN', 'TRX_STEEM', 'BTC_LINK', 'TRX_LINK', 'BTC_XTZ', 'USDT_XTZ', 'TRX_XTZ', 'USDT_BEAR', 'USDT_BULL', 'USDT_TRXBEAR', 'USDT_TRXBULL', 'PAX_BTC', 'PAX_ETH', 'USDT_PAX', 'USDT_USDJ', 'USDJ_BTC', 'USDJ_TRX', 'BTC_SNX', 'USDT_SNX', 'TRX_SNX', 'USDT_BSVBEAR', 'USDT_BSVBULL', 'BTC_MATIC', 'USDT_MATIC', 'TRX_MATIC', 'USDT_BCHBEAR', 'USDT_BCHBULL', 'USDT_ETHBEAR', 'USDT_ETHBULL', 'BTC_MKR', 'USDT_MKR', 'USDT_BVOL', 'USDT_IBVOL', 'DAI_BTC', 'DAI_ETH', 'USDT_DAI', 'BTC_NEO', 'USDT_NEO', 'TRX_NEO', 'BTC_SWFTC', 'USDT_SWFTC', 'TRX_SWFTC', 'USDT_JST', 'TRX_JST', 'BTC_FXC', 'USDT_FXC', 'TRX_FXC', 'USDT_BCN', 'USDT_STEEM', 'USDT_LINK', 'USDJ_BTT', 'BTC_AVA', 'USDT_AVA', 'TRX_AVA', 'USDT_XRPBULL', 'USDT_XRPBEAR', 'USDT_EOSBULL', 'USDT_EOSBEAR', 'USDT_LINKBULL', 'USDT_LINKBEAR', 'BTC_CHR', 'USDT_CHR', 'TRX_CHR', 'BNB_BTC', 'USDT_BNB', 'USDT_BUSD', 'TRX_BNB', 'BUSD_BNB', 'BUSD_BTC', 'BTC_MDT', 'USDT_MDT', 'TRX_MDT', 'USDT_BCHC', 'USDT_COMP', 'ETH_COMP', 'BTC_XFIL', 'USDT_XFIL', 'USDT_CUSDT', 'BTC_LEND', 'USDT_LEND', 'BTC_REN', 'USDT_REN', 'BTC_LRC', 'USDT_LRC', 'USDT_BAL', 'ETH_BAL', 'BTC_WRX', 'USDT_WRX', 'TRX_WRX', 'USDT_STAKE', 'USDT_BZRX', 'BTC_SXP', 'USDT_SXP', 'TRX_SXP', 'USDT_MTA', 'USDT_YFI', 'BTC_STPT', 'USDT_STPT', 'TRX_STPT', 'USDT_TRUMPWIN', 'USDT_TRUMPLOSE', 'USDT_DEC', 'USDT_PLT', 'USDT_UMA', 'USDT_KTON', 'USDT_RING', 'BTC_SWAP', 'USDT_SWAP', 'USDT_TEND', 'BTC_EXE', 'USDT_EXE', 'USDT_TRADE']
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