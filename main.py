from Poloniex import Poloniex
import datetime as dt
import json
import os
import time
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn import preprocessing
from sklearn.model_selection import train_test_split

def parse_prediction_results(dic):
    if amount_of_predictions % 100 != 0:
        raise Exception(f"amount_of_predictions is not a multiple of 100 it is: {amount_of_predictions}")
    
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
    Polo = Poloniex(API_Key,API_Secret)
    Last_Data_Refresh = 0
    prediction_results = {"Higher":[],"Lower":[]}
    if not os.path.exists("JSON"):
        os.mkdir("JSON")
    
    # TWEAKABLE CONFIGS HERE
    interval = 7200
    ticker = "USDT_BTC"
    amount_of_predictions = 10000 # NEEDS TO BE MULTIPLE OF 100

    # LOAD LAST RUN TIMES, ADD TICKER DEFAULT TO 0
    if not os.path.exists(f"JSON\\LastRunTimes_{interval}.json"):
        with open(f"JSON\\LastRunTimes_{interval}.json","w") as f:
            json.dump({},f)

    with open(f"JSON\\LastRunTimes_{interval}.json","r") as f:
        LastRunTimes = json.load(f)

    if ticker not in LastRunTimes:
        LastRunTimes[ticker] = 0

    LastRun = LastRunTimes[ticker]

    while True:    
        time_since_run = dt.datetime.now().timestamp() - LastRun
        if time_since_run >= interval:
            print(f"It has been {time_since_run} seconds since last run. running now..")
            now_ts = dt.datetime.now().timestamp()
            LastRun = now_ts
            LastRunTimes[ticker] = LastRun
            with open(f"JSON\\LastRunTimes_{interval}.json","w") as f:
                json.dump(LastRunTimes,f)
        else:
            print(f"Not been {interval} seconds since last run, it has been {time_since_run}, sleeping for 1 minute.")
            time.sleep(60)
            continue        

        # REFRESH ALL OPEN POSITIONS
        open_positions = Polo.load_all_open_positions()

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
 
        # CREATE DF AND DUMP TO CSV
        df = Polo.create_df(ticker,interval, dt.datetime(2018,1,1))
        df.drop(["high","low","open","volume","quoteVolume","weightedAverage"],axis=1,inplace=True)
        next_interval = dt.datetime.strptime(df.tail(1).index.item(), "%Y-%m-%d %H:%M:%S") + dt.timedelta(seconds=interval)
        df["shifted_prediction"] = df["close"].shift(-1)
        df.rename(columns={"close":"actual_close"},inplace=True)

        # GENERATE JSON LOG IF NOT PRESENT OR LOAD EXISTING
        json_string = df.to_json(orient="index")
        new_json_data = json.loads(json_string)

        if not os.path.exists(f"JSON\\{ticker}_{interval}_log.json"):
            with open(f"JSON\\{ticker}_{interval}_log.json","w")as f:
                json.dump(new_json_data,f,indent=2)

        with open(f"JSON\\{ticker}_{interval}_log.json","r") as f:
            json_file = json.load(f)

        # GENERATE LAST 31 INTERVALS TO SPEED UP JSON EDITING
        last_31_intervals_keys = list(json_file.keys())
        last_31_intervals_keys = last_31_intervals_keys[-31:]

        # UPDATE ALL LOG RECORDS WITH THE ACTUAL CLOSE, IF MISSING, CHECK IF PAST PREDICTIONS ARE CORRECT
        update_count = 0
        ignore_keys = ["LRPrediction","PredictedDirectionFromCurrent","CurrentPriceWhenPredicted"]

        # LOAD ANY MISSING DATA
        for date in new_json_data:
            if date not in json_file:
                json_file[date] = new_json_data[date]
        
        # FORMAT ALL THE DATA
        for date in json_file:
            if date not in last_31_intervals_keys:
                continue

            if date in new_json_data:
                for key in json_file[date]:
                    if key in ignore_keys:
                        continue

                    if key == "CorrectPrediction":
                        if json_file[date]["PredictedDirectionFromCurrent"] == "Lower":
                            if type(json_file[date]["actual_close"]) is not float:
                                continue
                            elif type(json_file[date]["CurrentPriceWhenPredicted"]) is not float:
                                continue
                            if json_file[date]["CurrentPriceWhenPredicted"] > json_file[date]["actual_close"]:
                                json_file[date]["CorrectPrediction"] = True
                            else:
                                json_file[date]["CorrectPrediction"] = False
                        else:
                            if type(json_file[date]["actual_close"]) is not float:
                                continue
                            elif type(json_file[date]["CurrentPriceWhenPredicted"]) is not float:
                                continue
                            if json_file[date]["CurrentPriceWhenPredicted"] < json_file[date]["actual_close"]:
                                json_file[date]["CorrectPrediction"] = True
                            else:
                                json_file[date]["CorrectPrediction"] = False

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
        
        # Calc % chance of lower/higher
        direction, percentage, average = parse_prediction_results(prediction_results)
        print(f"Predictions have calculated that there is a {percentage}% chance of the price being {direction} than the current price of: {current_price} at the next interval of: {next_interval}.\nAverage price predicted: {average}")
        
        # UPDATE JSON DICT WITH NEW PREDICTION DATA AND DUMP IT
        json_file[dt.datetime.strftime(next_interval,"%Y-%m-%d %H:%M:%S")] = {"actual_close":None,"shifted_prediction":None,"LRPrediction":average,"PredictedDirectionFromCurrent":direction,"CurrentPriceWhenPredicted":current_price,"CorrectPrediction":None}

        with open(f"JSON\\{ticker}_{interval}_log.json","w")as f:
            json.dump(json_file,f,indent=2,sort_keys=True)

        #TODO ALL THE TRADING LOGIC HERE BASED ON DIRECTION AND IF I HAVE ANY OPEN TRADES OF THAT TICKER
        if ticker in open_positions:
            print(f"Not initiating trade, position already open for ticker {ticker}.")
        if direction == "Lower":
            trade_type = "sell"
        else:
            trade_type = "buy"