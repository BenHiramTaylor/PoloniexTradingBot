from Poloniex import Poloniex

if __name__ == "__main__":
    API_Secret = ""
    API_Key = ""
    Polo = Poloniex(API_Key,API_Secret)
    print(Polo.execute_command('returnBalances'))
