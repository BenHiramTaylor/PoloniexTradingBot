import datetime as dt
import json
import os
import time
from typing import Optional

import pandas as pd
from loguru import logger
from statsmodels.tsa.arima.model import ARIMA

from app.api.exceptions import PoloniexError
from app.api.poloniex import Poloniex
from app.config import Config
from app.utils import load_config, load_df_from_json

if __name__ == "__main__":

    next_interval = None

    json_dir = "./JSON"

    if not os.path.exists(json_dir):
        os.mkdir(json_dir)

    while True:

        conf: Config = load_config(path="./config.yaml")
        polo = Poloniex(conf.poloniex)
        auto_trade: Optional[bool] = conf.auto_trade
        interval: Optional[float] = conf.interval
        ticker: Optional[str] = conf.ticker

        # LOAD LAST RUN TIMES, ADD TICKER DEFAULT TO 0
        interval_json = os.path.join(json_dir, f"LastRunTimes_{interval}.json")
        price_log_json = os.path.join(json_dir, f"{ticker}_{interval}_price_log.json")
        trade_log_json = os.path.join(json_dir, f"{ticker}_{interval}_trade_log.json")

        if not os.path.exists(path=interval_json):
            with open(file=interval_json, mode="w") as f:
                json.dump({}, f)

        with open(file=interval_json, mode="r") as f:
            LastRunTimes = json.load(f)

        if ticker not in LastRunTimes:
            LastRunTimes[ticker] = 0

        LastRun = LastRunTimes[ticker]

        if not next_interval:
            time_since_run = dt.datetime.now().timestamp() - LastRun
            if LastRun == 0:
                logger.info("Bot never run before, running for first time...")
            elif time_since_run >= interval:
                logger.info(
                    f"It has been {time_since_run} seconds since last run. running"
                    " now.."
                )
            else:
                last_run_dt = dt.datetime.fromtimestamp(LastRun)
                next_interval = last_run_dt + dt.timedelta(seconds=interval)
                continue
        else:
            next_interval = next_interval + dt.timedelta(seconds=60)
            next_interval_sleep = (
                next_interval.timestamp() - dt.datetime.now().timestamp()
            )
            if next_interval_sleep > 0:
                next_interval_string = dt.datetime.strftime(
                    next_interval, "%Y-%m-%d %H:%M:%S"
                )
                logger.info(
                    "We have the next interval, sleeping until then. See you in"
                    f" {next_interval_sleep} seconds at {next_interval_string}"
                )
                time.sleep(next_interval_sleep)

        # REFRESH ALL OPEN POSITIONS
        open_positions = polo.load_all_open_positions()
        killed_positions = False

        # KILL ALL POSITITONS THAT ARE 2 DAYS OLD
        if len(open_positions):
            for t in open_positions:
                for p in open_positions[t]:
                    two_days_ago = dt.datetime.now() - dt.timedelta(days=2)
                    trade_date = dt.datetime.strptime(
                        open_positions[t][p]["date"], "%Y-%m-%d %H:%M:%S"
                    )
                    order_number = int(open_positions[t][p]["orderNumber"])
                    if trade_date < two_days_ago:
                        logger.success(
                            f"Killing {open_positions[t][p]['type']} order with order"
                            f" number {order_number}\nPosition was opened on:"
                            f" {open_positions[t][p]['date']}"
                        )
                        polo.api_query("cancelOrder", {"orderNumber": order_number})
                        killed_positions = True

            if killed_positions:
                # REFRESH ALL OPEN POSITIONS AFTER KILLING OLD ONES
                open_positions = polo.load_all_open_positions()

        # CREATE DF AND DUMP TO JSON
        if not os.path.exists(path=price_log_json):
            logger.info("Loading full DataFrame.")
            df = polo.auto_create_df(ticker, interval, full_df=True)
            df.drop(
                ["high", "low", "open", "volume", "quoteVolume", "weightedAverage"],
                axis=1,
                inplace=True,
            )
            json_string = df.to_json(orient="index")
            new_json_data = json.loads(json_string)
            with open(file=price_log_json, mode="w") as f:
                json.dump(new_json_data, f, indent=2, sort_keys=True)
            # GET PREVIOUS CLOSE FOR HIGHER/LOWER CHECKS
            previous_close = df.tail(2).head(1)["close"].item()
            current_interval = dt.datetime.strptime(
                df.tail(1).index.item(), "%Y-%m-%d %H:%M:%S"
            )
            next_interval = current_interval + dt.timedelta(seconds=interval)
        else:
            logger.info("Loading existing DataFrame and updating with new records.")
            df = load_df_from_json(file_path=price_log_json)

        while True:
            # GET UPDATED DF
            new_df = polo.auto_create_df(ticker, interval)
            new_df.drop(
                ["high", "low", "open", "volume", "quoteVolume", "weightedAverage"],
                axis=1,
                inplace=True,
            )
            # GET PREVIOUS CLOSE FOR HIGHER/LOWER CHECKS
            previous_close = new_df.tail(2).head(1)["close"].item()
            current_interval = dt.datetime.strptime(
                new_df.tail(1).index.item(), "%Y-%m-%d %H:%M:%S"
            )
            next_interval = current_interval + dt.timedelta(seconds=interval)
            if next_interval.timestamp() - dt.datetime.now().timestamp() > 0:
                break
            else:
                print_current_interval = dt.datetime.strftime(
                    current_interval, "%Y-%m-%d %H:%M:%S"
                )
                logger.warning(
                    f"Current interval received was {print_current_interval}, which"
                    " should be wrong, sleeping for 5 seconds and reloading DataFrame"
                )
                time.sleep(5)

        df = pd.concat(objs=[df, new_df])
        df = (
            df.reset_index()
            .drop_duplicates(subset="period", keep="first")
            .set_index("period")
        )
        json_string = df.to_json(orient="index")
        new_json_data = json.loads(json_string)
        with open(file=price_log_json, mode="w") as f:
            json.dump(new_json_data, f, indent=2, sort_keys=True)

        # LOG TIMESTAMP OF LAST INTERVAL TO FILE
        LastRunTimes[ticker] = current_interval.timestamp()
        with open(file=interval_json, mode="w") as f:
            json.dump(LastRunTimes, f)

        with open(file=price_log_json, mode="r") as f:
            json_file = json.load(f)

        # OPEN TRADE LOG
        if not os.path.exists(path=trade_log_json):
            with open(file=trade_log_json, mode="w") as f:
                json.dump({}, f)
        with open(file=trade_log_json, mode="r") as f:
            trade_log = json.load(f)

        # UPDATE ALL LOG RECORDS WITH THE ACTUAL CLOSE, IF MISSING, CHECK IF PAST PREDICTIONS ARE CORRECT
        update_count = 0
        for date in trade_log:
            if date in new_json_data:
                if new_json_data[date]["close"] != trade_log[date]["close"]:
                    update_count += 1
                    trade_log[date]["close"] = new_json_data[date]["close"]

        for date in trade_log:
            if trade_log[date]["correct_prediction"] is not None:
                continue
            if trade_log[date]["predicted_direction_from_current"] == "Lower":
                if type(trade_log[date]["close"]) is not float:
                    continue
                elif type(trade_log[date]["previous_close"]) is not float:
                    continue
                if trade_log[date]["previous_close"] > trade_log[date]["close"]:
                    trade_log[date]["correct_prediction"] = True
                else:
                    trade_log[date]["correct_prediction"] = False
            else:
                if type(trade_log[date]["close"]) is not float:
                    continue
                elif type(trade_log[date]["previous_close"]) is not float:
                    continue
                if trade_log[date]["previous_close"] < trade_log[date]["close"]:
                    trade_log[date]["correct_prediction"] = True
                else:
                    trade_log[date]["correct_prediction"] = False

        if update_count > 0:
            logger.success(f"Updated JSON Trade Log with {update_count} new records.")

        # GRAB ONLY LAST THIRD OF THE DATAFRAME
        third = int(len(df) * 0.66)
        df = df.iloc[third:]

        # TRAIN THE DATA TO GET PREDICTIONS
        x = new_df["close"].values

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

        # PRINT THE RESULTS FROM THE PREDICTION
        logger.success(
            f"Predictions have predicted the price being {direction} than the previous"
            f" close of: {previous_close} at the next interval of:"
            f" {next_interval}.\nPrice predicted: {result}, price difference is"
            f" {difference}."
        )

        # ALL THE TRADING LOGIC HERE BASED ON DIRECTION AND IF THERE ARE ANY OPEN TRADES OF THAT TICKER
        # ONLY TRADES IF % CHANCE IS > 75% AND IF AUTOTRADE IS SET TO TRUE
        if auto_trade:
            if difference >= 5:

                # если нужно продавать - то продаем на 1 процент
                # от общего кол-ва второй позиции в тикере
                # если нужно покупать, то покупаем на 1 процент от
                # первой позиции в тикере
                if direction == "Lower":
                    trade_type = "sell"
                    currency = ticker.split("_")[1]
                else:
                    trade_type = "buy"
                    currency = ticker.split("_")[0]

                if ticker in open_positions:
                    logger.info(
                        "Not initiating trade, position already open for ticker"
                        f" {ticker}."
                    )
                    took_trade = False
                else:

                    #  GET BALANCE
                    balance = polo.get_balance(currency)
                    # IF TRADE TYPE IS BUY AND BALANCE == 0
                    if balance == 0:

                        if trade_type == "buy":
                            raise PoloniexError(
                                "Your Balance is 0. Please deposit and restart the bot."
                            )
                        else:
                            took_trade = False
                            logger.info("Nothing selling wait next time.")

                    else:

                        trade_amount = polo.get_1_percent_trade_size(ticker, currency)

                        rate = polo.get_current_price(ticker)

                        logger.info(
                            f"Placing Trade for ticker: {ticker}, {trade_type}ing an"
                            f" amount of {trade_amount} at a rate of {rate} per 1."
                        )

                        trade_params = {
                            "currencyPair": ticker,
                            "rate": rate,
                            "amount": trade_amount,
                        }

                        polo.api_query(trade_type, trade_params)
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

        # UPDATE JSON DICT WITH NEW PREDICTION DATA AND DUMP IT
        trade_log[dt.datetime.strftime(current_interval, "%Y-%m-%d %H:%M:%S")] = {
            "close": None,
            "prediction": result,
            "predicted_direction_from_current": direction,
            "previous_close": previous_close,
            "correct_prediction": None,
            "took_trade": took_trade,
        }

        with open(file=trade_log_json, mode="w") as f:
            json.dump(trade_log, f, indent=2, sort_keys=True)
