import datetime

import ccxt
from loguru import logger
from pandas import DataFrame
from statsmodels.tsa.arima.model import ARIMA

from config import Config
from exceptions import TraderBotLowBalanceError
from utils import get_1_percent_trade_size, get_current_price, load_config

conf: Config = load_config("./config.yaml")

polo = ccxt.poloniex(
    {"apiKey": conf.poloniex.api_key, "secret": conf.poloniex.api_secret}
)


data = polo.fetch_ohlcv(
    symbol=conf.ticker,
    timeframe="2h",
    since=int(datetime.datetime(year=2018, month=1, day=1).timestamp() * 1000),
)

df = DataFrame(data=data, columns=["date", "high", "low", "open", "close", "volume"])

df["date"] = df["date"].map(
    lambda x: datetime.datetime.strftime(
        datetime.datetime.fromtimestamp(x / 1000), "%Y-%m-%d %H:%M:%S"
    )
)
df.set_index("date", inplace=True)


# GRAB ONLY LAST THIRD OF THE DATAFRAME
third = int(len(df) * 0.66)
df = df.iloc[third:]

# TRAIN THE DATA TO GET PREDICTIONS
x = df["close"].values
#  GET PREVIOUS CLOSE VALUE
previous_close = x[-2]

model = ARIMA(x, order=(5, 1, 0))
model_fit = model.fit(method="statespace", method_kwargs=dict(disp=0))
output = model_fit.forecast()
result = output[0]

# LOG PREDICTIONS BASED ON CURRENT PRICE
if result > previous_close:
    direction = "Higher"
    difference = result - previous_close
else:
    direction = "Lower"
    difference = previous_close - result

print(result, direction, difference)


if conf.auto_trade:
    if difference >= 0:

        # если нужно продавать - то продаем на 1 процент
        # от общего кол-ва второй позиции в тикере
        # если нужно покупать, то покупаем на 1 процент от
        # первой позиции в тикере
        if direction == "Lower":
            trade_type = "sell"
            currency = conf.ticker.split("_")[1]
        else:
            trade_type = "buy"
            currency = conf.ticker.split("_")[0]

        open_positions = polo.fetch_open_orders()
        if conf.ticker in open_positions:
            logger.info(
                f"Not initiating trade, position already open for ticker {conf.ticker}."
            )
            took_trade = False
        else:

            #  GET BALANCE
            balance = polo.fetch_balance()[currency]
            # IF TRADE TYPE IS BUY AND BALANCE == 0

            if balance["free"] == 0:
                if trade_type == "buy":
                    raise TraderBotLowBalanceError(
                        "Your Balance is 0. Please deposit and restart the bot."
                    )
                else:
                    took_trade = False
                    logger.info("Nothing selling wait next time.")

            else:

                trade_amount = get_1_percent_trade_size(
                    client=polo, ticker=conf.ticker, currency=currency
                )

                rate = get_current_price(ticker=conf.ticker)

                logger.info(
                    f"Placing Trade for ticker: {conf.ticker}, {trade_type}ing an"
                    f" amount of {trade_amount} at a rate of {rate} per 1."
                )

                trade_params = {
                    "currencyPair": conf.ticker,
                    "rate": rate,
                    "amount": trade_amount,
                }
                polo.create_order(
                    symbol=conf.ticker, type=trade_type, amount=trade_params, price=rate
                )
                took_trade = True
    else:
        took_trade = False
        logger.info(
            f"Not initiating trade, predicted price difference was less than 5."
        )
else:
    took_trade = False
    logger.info(
        "Not Trading, AutoTrade is set to False, "
        "to change this, please set AutoTrade to true in APISettings.json"
    )
