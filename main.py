from Poloniex import Poloniex, PoloniexError
import datetime as dt
import json
import os
import time
import numpy as np
from statsmodels.tsa.arima_model import ARIMA

def refresh_configs():
    global API_Secret, API_Key, auto_trade, interval, ticker, amount_of_predictions, amount_of_training_iterations, model_file_path

    with open('APISettings.json','r') as f:
        config = json.load(f)
    API_Secret = config["API_Secret"]
    API_Key = config["API_Key"]
    # LOAD TWEAKABLE CONFIGS FROM APISettings.json
    auto_trade = config["AutoTrade"]
    interval = config["Interval"]
    ticker = config["Ticker"]

if __name__ == "__main__":
    # GENERATE DEFAULT SETTINGS
    with open('APISettings.json','r') as f:
        config = json.load(f)
    API_Secret = config["API_Secret"]
    API_Key = config["API_Key"]
    # LOAD TWEAKABLE CONFIGS FROM APISettings.json
    auto_trade = None
    interval = None
    ticker = None

    # CREATE CLASS AND REQUIRED VARS
    Polo = Poloniex(API_Key,API_Secret)
    next_interval = False
    if not os.path.exists("JSON"):
        os.mkdir("JSON")

    while True:
        # REFRESH CONFIGS EACH RUN
        refresh_configs()

        # LOAD LAST RUN TIMES, ADD TICKER DEFAULT TO 0
        if not os.path.exists(f"JSON\\LastRunTimes_{interval}.json"):
            with open(f"JSON\\LastRunTimes_{interval}.json","w") as f:
                json.dump({},f)

        with open(f"JSON\\LastRunTimes_{interval}.json","r") as f:
            LastRunTimes = json.load(f)

        if ticker not in LastRunTimes:
            LastRunTimes[ticker] = 0

        LastRun = LastRunTimes[ticker]

        if not next_interval:
            time_since_run = dt.datetime.now().timestamp() - LastRun
            if LastRun == 0:
                print("Bot never run before, running for first time...")
            elif time_since_run >= interval:
                print(f"It has been {time_since_run} seconds since last run. running now..")
            else:
                last_run_dt = dt.datetime.fromtimestamp(LastRun)
                next_interval = last_run_dt + dt.timedelta(seconds=interval)
                continue
        else:
            next_interval = next_interval + dt.timedelta(seconds=60)
            next_interval_sleep = next_interval.timestamp()-dt.datetime.now().timestamp()
            if next_interval_sleep > 0:
                next_interval_string = dt.datetime.strftime(next_interval,"%Y-%m-%d %H:%M:%S")
                print(f"We have the next interval, sleeping until then. See you in {next_interval_sleep} seconds at {next_interval_string}")
                time.sleep(next_interval_sleep)

        # REFRESH ALL OPEN POSITIONS
        open_positions = Polo.load_all_open_positions()
        killed_positions = False

        # KILL ALL POSITITONS THAT ARE 2 DAYS OLD
        if len(open_positions):
            for t in open_positions:
                for p in open_positions[t]:
                    two_days_ago = dt.datetime.now() - dt.timedelta(days=2)
                    trade_date = dt.datetime.strptime(open_positions[t][p]["date"], "%Y-%m-%d %H:%M:%S")
                    order_number = int(open_positions[t][p]["orderNumber"])
                    if trade_date < two_days_ago:
                        print(f"Killing {open_positions[t][p]['type']} order with order number {order_number}\nPosition was opened on: {open_positions[t][p]['date']}")
                        Polo.api_query("cancelOrder",{"orderNumber":order_number})
                        killed_positions = True

            if killed_positions:
                # REFRESH ALL OPEN POSITIONS AFTER KILLING OLD ONES
                open_positions = Polo.load_all_open_positions()
        
        # CREATE DF AND DUMP TO JSON
        if not os.path.exists(f"JSON\\{ticker}_{interval}_log.json"):
            print("Loading full DataFrame.")
            df = Polo.auto_create_df(ticker,interval,full_df=True)
            df.drop(["high","low","open","volume","quoteVolume","weightedAverage"],axis=1,inplace=True)
            json_string = df.to_json(orient="index")
            new_json_data = json.loads(json_string)
            with open(f"JSON\\{ticker}_{interval}_log.json","w")as f:
                json.dump(new_json_data,f,indent=2)
            # GET PREVIOUS CLOSE FOR HIGHER/LOWER CHECKS
            previous_close = df.tail(2).head(1)['close'].item()
            current_interval = dt.datetime.strptime(df.tail(1).index.item(), "%Y-%m-%d %H:%M:%S")
            next_interval =  current_interval + dt.timedelta(seconds=interval)
        else:
            print("Loading existing DataFrame and updating with new records.")
            df = Polo.load_df_from_json(f"JSON\\{ticker}_{interval}_log.json")
            df.drop(["correct_prediction","predicted_direction_from_current","prediction","previous_close"], axis=1, inplace=True)
            df.dropna(inplace=True)
            while True:
                # GET UPDATED DF AND JOIN
                new_df = Polo.auto_create_df(ticker,interval)
                new_df.drop(["high","low","open","volume","quoteVolume","weightedAverage"],axis=1,inplace=True)
                # GET PREVIOUS CLOSE FOR HIGHER/LOWER CHECKS
                previous_close = new_df.tail(2).head(1)['close'].item()
                current_interval = dt.datetime.strptime(new_df.tail(1).index.item(), "%Y-%m-%d %H:%M:%S")
                next_interval =  current_interval + dt.timedelta(seconds=interval)
                if next_interval.timestamp()-dt.datetime.now().timestamp() > 0:
                    break
                else:
                    print_current_interval = dt.datetime.strftime(current_interval, "%Y-%m-%d %H:%M:%S")
                    print(f"Next interval received was {print_current_interval}, which should be wrong, sleeping for 5 seconds and reloading DataFrame")
                    time.sleep(5)

            df = df.append(new_df)
            df = df.reset_index().drop_duplicates(subset='period', keep='first').set_index('period')
            json_string = df.to_json(orient="index")
            new_json_data = json.loads(json_string)
            with open(f"JSON\\{ticker}_{interval}_log.json","w")as f:
                json.dump(new_json_data,f,indent=2)

        # LOG TIMESTAMP OF LAST INTERVAL TO FILE
        LastRunTimes[ticker] = current_interval.timestamp()
        with open(f"JSON\\LastRunTimes_{interval}.json","w") as f:
            json.dump(LastRunTimes,f)

        with open(f"JSON\\{ticker}_{interval}_log.json","r") as f:
            json_file = json.load(f)

        # GET LAST 31 INTERVALS TO SPEED UP JSON EDITING
        last_31_intervals_keys = list(json_file.keys())
        last_31_intervals_keys = last_31_intervals_keys[-31:]

        # LOAD ANY MISSING DATA
        for date in new_json_data:
            if date not in json_file:
                json_file[date] = new_json_data[date]
        
        # UPDATE ALL LOG RECORDS WITH THE ACTUAL CLOSE, IF MISSING, CHECK IF PAST PREDICTIONS ARE CORRECT
        update_count = 0
        ignore_keys = ["prediction","predicted_direction_from_current","previous_close"]
        
        for date in json_file:
            if date not in last_31_intervals_keys:
                continue

            if date in new_json_data:
                for key in json_file[date]:
                    if key == "correct_prediction":
                        if json_file[date]["predicted_direction_from_current"] == "Lower":
                            if type(json_file[date]["close"]) is not float:
                                continue
                            elif type(json_file[date]["previous_close"]) is not float:
                                continue
                            if json_file[date]["previous_close"] > json_file[date]["close"]:
                                json_file[date]["correct_prediction"] = True
                            else:
                                json_file[date]["correct_prediction"] = False
                        else:
                            if type(json_file[date]["close"]) is not float:
                                continue
                            elif type(json_file[date]["previous_close"]) is not float:
                                continue
                            if json_file[date]["previous_close"] < json_file[date]["close"]:
                                json_file[date]["correct_prediction"] = True
                            else:
                                json_file[date]["correct_prediction"] = False
                    elif key in ignore_keys:
                        continue

                    elif new_json_data[date][key] != json_file[date][key]:
                        json_file[date][key] = new_json_data[date][key]
                        if json_file[date][key] is not None:
                            update_count += 1
                            print(f"Changing {key}: {json_file[date][key]} to {key}: {new_json_data[date][key]} for date {date} in log.")                        

        if update_count > 0:
            print(f"Updated JSON Log with {update_count} new records.")

        # TRAIN THE DATA TO GET PREDICTIONS
        x = df.values

        model = ARIMA(x, order=(5,1,0))
        model_fit = model.fit(disp=0)
        output = model_fit.forecast()
        result = output[0][0]
        # LOG PREDICTIONS BASED ON CURRENT PRICE
        if result > previous_close:
            direction = "Higher"
            difference = result - previous_close
        else:
            direction = "Lower"
            difference = previous_close - result
        
        # PRINT THE RESULTS FROM THE PREDICTION
        print(f"Predictions have predicted the price being {direction} than the previous close of: {previous_close} at the next interval of: {next_interval}.\nPrice predicted: {result}, price difference is {difference}.")

        # UPDATE JSON DICT WITH NEW PREDICTION DATA AND DUMP IT
        json_file[dt.datetime.strftime(current_interval,"%Y-%m-%d %H:%M:%S")] = {"close":None,"prediction":result,"predicted_direction_from_current":direction,"previous_close":previous_close,"correct_prediction":None}

        with open(f"JSON\\{ticker}_{interval}_log.json","w")as f:
            json.dump(json_file,f,indent=2,sort_keys=True)

        # ALL THE TRADING LOGIC HERE BASED ON DIRECTION AND IF THERE ARE ANY OPEN TRADES OF THAT TICKER 
        # ONLY TRADES IF % CHANCE IS > 75% AND IF AUTOTRADE IS SET TO TRUE
        if not auto_trade:
            print("Not Trading, AutoTrade is set to False, to change this, please set AutoTrade to true in APISettings.json")
            continue

        if difference >= 5:
            if direction == "Lower":
                trade_type = "sell"
            else:
                trade_type = "buy"
            if ticker in open_positions:
                print(f"Not initiating trade, position already open for ticker {ticker}.")
            else:
                trade_amount = Polo.get_1_percent_trade_size(ticker, "BTC")
                rate = Polo.get_current_price(ticker)
                print(f"Placing Trade for ticker: {ticker}, {trade_type}ing an amount of {trade_amount} at a rate of {rate} per 1.")
                trade_params = {"currencyPair":ticker, "rate":rate, "amount":trade_amount}
                Polo.api_query(trade_type, trade_params)
        else:
            print(f"Not initiating trade, predicted price difference was less than 5.")