from Poloniex import Poloniex, PoloniexError
import datetime as dt
import json
import os
import time
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn import preprocessing
from sklearn.model_selection import train_test_split

def refresh_configs():
    global API_Secret, API_Key, auto_trade, interval, ticker, amount_of_predictions

    with open('APISettings.json','r') as f:
        config = json.load(f)
    API_Secret = config["API_Secret"]
    API_Key = config["API_Key"]
    # LOAD TWEAKABLE CONFIGS FROM APISettings.json
    auto_trade = config["AutoTrade"]
    interval = config["Interval"]
    ticker = config["Ticker"]
    amount_of_predictions = config["Prediction_Iterations"] # NEEDS TO BE MULTIPLE OF 100

def parse_prediction_results(dic):
    if amount_of_predictions % 100 != 0:
        raise PoloniexError(f"amount_of_predictions is not a multiple of 100 it is: {amount_of_predictions}")
    
    scaler = 0
    average = float(0)
    
    if amount_of_predictions != 100:
        scaler = amount_of_predictions / 100

    if len(dic["Higher"]) > len(dic["Lower"]):
        direction = "Higher"
    else:
        direction = "Lower"
    print(f"Number of times predicted Higher: {len(dic['Higher'])}\nNumber of times predicted Lower: {len(dic['Lower'])}")

    for i in dic[direction]:
        average = average + i
        
    percentage = len(dic[direction])/scaler
    scaled_average = average/len(dic[direction])

    return direction, percentage, scaled_average

if __name__ == "__main__":
    # GENERATE DEFAULT SETTINGS
    with open('APISettings.json','r') as f:
        config = json.load(f)
    API_Secret = config["API_Secret"]
    API_Key = config["API_Key"]
    # LOAD TWEAKABLE CONFIGS FROM APISettings.json
    auto_trade = config["AutoTrade"]
    interval = config["Interval"]
    ticker = config["Ticker"]
    amount_of_predictions = config["Prediction_Iterations"] # NEEDS TO BE MULTIPLE OF 100

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
                print(f"Not been {interval} seconds since last run, it has been {time_since_run}, sleeping for 60 seconds.")
                time.sleep(60)
                continue
        else:
            next_interval = next_interval + dt.timedelta(seconds=10)
            next_interval_sleep = next_interval.timestamp()-dt.datetime.now().timestamp()
            if next_interval_sleep > 0:
                next_interval_string = dt.datetime.strftime(next_interval,"%Y-%m-%d %H:%M:%S")
                print(f"We have the next interval, sleeping until then. See you in {next_interval_sleep} seconds at {next_interval_string}")
                time.sleep(next_interval_sleep)

        #RESET DIC FOR PREDICTIONS
        prediction_results = {"Higher":[],"Lower":[]}    

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
 
        # CREATE DF AND DUMP TO CSV
        df = Polo.auto_create_df(ticker,interval)
        df.drop(["high","low","open","volume","quoteVolume","weightedAverage"],axis=1,inplace=True)
        last_interval = dt.datetime.strptime(df.tail(1).index.item(), "%Y-%m-%d %H:%M:%S")
        next_interval =  last_interval + dt.timedelta(seconds=interval)
        df["shifted_prediction"] = df["close"].shift(-1)
        df.rename(columns={"close":"actual_close"},inplace=True)

        # LOG TIMESTAMP OF LAST INTERVAL TO FILE
        LastRunTimes[ticker] = last_interval.timestamp()
        with open(f"JSON\\LastRunTimes_{interval}.json","w") as f:
            json.dump(LastRunTimes,f)

        # GENERATE JSON LOG IF NOT PRESENT OR LOAD EXISTING
        json_string = df.to_json(orient="index")
        new_json_data = json.loads(json_string)

        if not os.path.exists(f"JSON\\{ticker}_{interval}_log.json"):
            with open(f"JSON\\{ticker}_{interval}_log.json","w")as f:
                json.dump(new_json_data,f,indent=2)

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
        ignore_keys = ["lr_prediction","predicted_direction_from_current","current_price_when_predicted"]
        
        for date in json_file:
            if date not in last_31_intervals_keys:
                continue

            if date in new_json_data:
                for key in json_file[date]:
                    if key in ignore_keys:
                        continue

                    if key == "correct_prediction":
                        if json_file[date]["predicted_direction_from_current"] == "Lower":
                            if type(json_file[date]["actual_close"]) is not float:
                                continue
                            elif type(json_file[date]["current_price_when_predicted"]) is not float:
                                continue
                            if json_file[date]["current_price_when_predicted"] > json_file[date]["actual_close"]:
                                json_file[date]["correct_prediction"] = True
                            else:
                                json_file[date]["correct_prediction"] = False
                        else:
                            if type(json_file[date]["actual_close"]) is not float:
                                continue
                            elif type(json_file[date]["current_price_when_predicted"]) is not float:
                                continue
                            if json_file[date]["current_price_when_predicted"] < json_file[date]["actual_close"]:
                                json_file[date]["correct_prediction"] = True
                            else:
                                json_file[date]["correct_prediction"] = False

                    elif new_json_data[date][key] != json_file[date][key]:
                        json_file[date][key] = new_json_data[date][key]
                        if json_file[date][key] is not None:
                            update_count += 1
                            print(f"Changing {key}: {json_file[date][key]} to {key}: {new_json_data[date][key]} for date {date} in log.")                        

        if update_count > 0:
            print(f"Updated JSON Log with {update_count} new records.")

        # DROP NA RECORDS AFRER UPDATING JSON WITH CLOSE
        df.dropna(inplace=True)

        # GET CURRENT PRICE FOR HIGHER/LOWER CHECKS
        current_price = Polo.get_current_price(ticker)

        # TRAIN THE DATA TO GET %
        Start_time = dt.datetime.now().timestamp()
        for i in range(amount_of_predictions):
            # MANIPLULATE DATA FOR TRAINING
            future_forecast_time = 1
            x = np.array(df.drop(["shifted_prediction"], 1))
            y = np.array(df["shifted_prediction"])
            x = preprocessing.scale(x)
            x_prediction = x[-future_forecast_time:]
            x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.5)

            # REGRESS THE TRAINING DATA
            clf = LinearRegression()
            clf.fit(x_train, y_train)
            prediction = (clf.predict(x_prediction))
            
            # LOG PREDICTIONS BASED ON CURRENT PRICE
            if prediction[0] > current_price:
                prediction_results["Higher"].append(prediction[0])
            else:
                prediction_results['Lower'].append(prediction[0])

        print(f"Took: {dt.datetime.strftime(dt.datetime.fromtimestamp(dt.datetime.now().timestamp() - Start_time), '%H:%M:%S')} to predict for ticker: {ticker} doing {amount_of_predictions} iterations.")
        
        # CALC % CHANCE OF LOWER/HIGHER
        direction, percentage, average = parse_prediction_results(prediction_results)
        print(f"Predictions have calculated that there is a {percentage}% chance of the price being {direction} than the current price of: {current_price} at the next interval of: {next_interval}.\nAverage price predicted: {average}")
        
        # UPDATE JSON DICT WITH NEW PREDICTION DATA AND DUMP IT
        json_file[dt.datetime.strftime(next_interval,"%Y-%m-%d %H:%M:%S")] = {"actual_close":None,"shifted_prediction":None,"lr_prediction":average,"predicted_direction_from_current":direction,"current_price_when_predicted":current_price,"correct_prediction":None}

        with open(f"JSON\\{ticker}_{interval}_log.json","w")as f:
            json.dump(json_file,f,indent=2,sort_keys=True)

        # ALL THE TRADING LOGIC HERE BASED ON DIRECTION AND IF THERE ARE ANY OPEN TRADES OF THAT TICKER 
        # ONLY TRADES IF % CHANCE IS > 75% AND IF AUTOTRADE IS SET TO TRUE
        if not auto_trade:
            print("Not Trading, AutoTrade is set to False, to change this, please set AutoTrade to true in APISettings.json")
            continue

        if percentage >= 75:
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
            print(f"Not initiating trade, got less than 75% chance on prediction: got {percentage}%")