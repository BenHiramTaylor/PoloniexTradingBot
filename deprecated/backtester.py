import datetime as dt
import json
import os

import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

from app.api.poloniex import Poloniex
from app.config import Config
from app.utils import load_config

if __name__ == "__main__":
    # CONFIGURABLE SETTINGS
    arima_order = (5, 1, 0)
    training_data_days = 98

    conf: Config = load_config(path="./config.yaml")

    interval = conf.interval
    ticker = conf.ticker

    json_dir = "./BACKTESTING"

    trade_log = os.path.join(
        json_dir,
        f"{ticker}_{interval}_trade_log_arima_order_{str(arima_order)}_training_data_days_{str(training_data_days)}.json",
    )

    price_logs = os.path.join(
        json_dir,
        f"{ticker}_{interval}_price_log.json",
    )

    polo: Poloniex = Poloniex(config=conf.poloniex)
    start_day = dt.datetime(2019, 8, 1)
    last_day = start_day + dt.timedelta(days=training_data_days)
    training_dates = []

    # GENERATE ALL INTERVALS BETWEEN THE PERIOD
    start_day_string = dt.datetime.strftime(start_day, "%Y-%m-%d %H:%M:%S")
    last_day_string = dt.datetime.strftime(last_day, "%Y-%m-%d %H:%M:%S")
    while True:
        if start_day >= last_day:
            print(
                f"Loaded all {len(training_dates)} intervals between"
                f" {start_day_string} and {last_day_string}"
            )
            break

        string_datetime = dt.datetime.strftime(start_day, "%Y-%m-%d %H:%M:%S")
        training_dates.append(string_datetime)
        start_day = start_day + dt.timedelta(seconds=interval)

    if not os.path.exists(json_dir):
        os.mkdir(json_dir)

    if not os.path.exists(path=trade_log):
        with open(
            trade_log,
            "w",
        ) as f:
            json.dump({}, f)

    if not os.path.exists(price_logs):
        print("Loading full DataFrame.")
        df = polo.auto_create_df(ticker, interval, full_df=True)
        df.drop(
            ["high", "low", "open", "volume", "quoteVolume", "weightedAverage"],
            axis=1,
            inplace=True,
        )
        json_string = df.to_json(orient="index")
        new_json_data = json.loads(json_string)
        with open(price_logs, "w") as f:
            json.dump(new_json_data, f, indent=2, sort_keys=True)

    with open(price_logs, "r") as f:
        all_data = json.load(f)
    # GET FINAL DATE FROM ALL DATA TO STOP
    final_date_string = list(all_data.keys())[-1]
    final_date = dt.datetime.strptime(final_date_string, "%Y-%m-%d %H:%M:%S")
    # LOAD ./Backtesting DATA
    Backtesting_data = {}
    for key in sorted(training_dates):
        if key in all_data:
            Backtesting_data[key] = all_data[key]
    print(f"Loaded initial ./Backtesting dataframe of {len(Backtesting_data)} values.")

    while True:
        # OPEN TRADE LOG
        with open(
            trade_log,
            "r",
        ) as f:
            trade_log = json.load(f)

        # CREATE DF FROM ./Backtesting DATA DICT
        df = pd.DataFrame.from_dict(Backtesting_data, orient="index")
        df.index.name = "period"
        df.index = df.index.astype(str)
        x = df["close"].values
        # GET PREVIOUS CLOSE FOR HIGHER/LOWER CHECKS
        previous_close = df.tail(2).head(1)["close"].item()
        current_interval = dt.datetime.strptime(
            df.tail(1).index.item(), "%Y-%m-%d %H:%M:%S"
        )
        next_interval = current_interval + dt.timedelta(seconds=interval)
        next_interval_string = dt.datetime.strftime(next_interval, "%Y-%m-%d %H:%M:%S")
        training_dates.append(next_interval_string)

        # TRAIN THE MODEL
        model = ARIMA(x, order=arima_order)
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

        # ALL THE TRADING LOGIC HERE BASED ON DIRECTION AND IF THERE ARE ANY OPEN TRADES OF THAT TICKER
        if difference >= 5:
            took_trade = True
        else:
            took_trade = False

        # UPDATE JSON DICT WITH NEW PREDICTION DATA AND DUMP IT
        trade_log[dt.datetime.strftime(current_interval, "%Y-%m-%d %H:%M:%S")] = {
            "close": None,
            "prediction": result,
            "predicted_direction_from_current": direction,
            "previous_close": previous_close,
            "correct_prediction": None,
            "took_trade": took_trade,
        }

        # ADD NEXT INTERVAL DATA TO Backtesting DATA
        first_key = list(Backtesting_data.keys())[0]
        current_interval_string = dt.datetime.strftime(
            current_interval, "%Y-%m-%d %H:%M:%S"
        )
        print(f"Backtested data using {first_key} to {current_interval_string}.")
        if next_interval_string in all_data:
            Backtesting_data[next_interval_string] = all_data[next_interval_string]
        # DELETE OLDEST VAL
        del Backtesting_data[first_key]

        # UPDATE CLOSE PRICES
        update_trade_log = list()
        for date in trade_log:
            if date in all_data:
                if all_data[date]["close"] != trade_log[date]["close"]:
                    trade_log[date]["close"] = all_data[date]["close"]
                    update_trade_log.append(date)
        # UPDATE TRADE LOG DATA NOW WE HAVE CLOSE
        for date in update_trade_log:
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

        with open(
            trade_log,
            "w",
        ) as f:
            json.dump(trade_log, f, indent=2, sort_keys=True)

        if next_interval > final_date:
            print("Reached the end of ./Backtesting, stopping now.")
            break

    total_predictions = list()
    correct_predictions = list()
    trades_taken = list()
    correct_trades_taken = list()
    could_have_taken = list()
    could_have_taken_correct = list()
    with open(
        trade_log,
        "r",
    ) as f:
        data = json.load(f)

    for period in data:
        if data[period]["correct_prediction"] is None:
            continue

        total_predictions.append(1)

        if data[period]["correct_prediction"]:
            correct_predictions.append(1)

        if data[period]["took_trade"]:
            trades_taken.append(1)
            if data[period]["correct_prediction"]:
                correct_trades_taken.append(1)

        if data[period]["predicted_direction_from_current"] == "Higher":
            if (data[period]["prediction"] - data[period]["previous_close"]) > 5:
                could_have_taken.append(1)
                if (data[period]["close"] - data[period]["previous_close"]) > 5:
                    could_have_taken_correct.append(1)
        else:
            if (data[period]["previous_close"] - data[period]["prediction"]) > 5:
                could_have_taken.append(1)
                if (data[period]["previous_close"] - data[period]["close"]) > 5:
                    could_have_taken_correct.append(1)

    if len(total_predictions) > 0:
        prediction_percentage = len(correct_predictions) / len(total_predictions) * 100
    else:
        prediction_percentage = 0

    if len(trades_taken) > 0:
        taken_percentage = len(correct_trades_taken) / len(trades_taken) * 100
    else:
        taken_percentage = 0
    profit_percentage = len(could_have_taken_correct) / len(could_have_taken) * 100
    print(
        "Total number of correct predictions"
        f" {len(correct_predictions)}/{len(total_predictions)} This is an overall"
        f" accuracy of {prediction_percentage}%\nOut of this amount"
        f" {len(trades_taken)} were taken and {len(correct_trades_taken)} of those were"
        f" correct, this is an actual accuracy of {taken_percentage}%.\nOut of"
        f" {len(total_predictions)} predictions, {len(could_have_taken)} trades could"
        f" have been taken.\nOut of that amount, {len(could_have_taken_correct)} would"
        " have been profitable.\nThat is a possible profitability percentage of"
        f" {profit_percentage}%"
    )
