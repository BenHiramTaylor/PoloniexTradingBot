from Poloniex import Poloniex

if __name__ == "__main__":
    API_Secret = ""
    API_Key = ""
    Polo = Poloniex(API_Key,API_Secret)
    btc_usd = Polo.execute_command('returnTicker')['USDC_BTC']
    print(btc_usd)
