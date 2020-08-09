import Poloniex

if __name__ == "__main__":
    precition = Poloniex.predict_next_close(86400, "USDT_BTC")
    print(precition)