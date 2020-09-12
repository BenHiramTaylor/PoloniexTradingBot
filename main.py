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
    # GENERATE CONFIGS AND DEFAULT SETTINGS 
    with open('APISettings.json','r') as f:
        config = json.load(f)
    API_Secret = config["API_Secret"]
    API_Key = config["API_Key"]
    LastRun = 0
    Polo = Poloniex(API_Key,API_Secret)
    if not os.path.exists("JSON"):
        os.mkdir("JSON")
    interval = 7200
    ticker = "USDT_BTC"
    amount_of_predictions = 10000 # NEEDS TO BE MULTIPLE OF 100
    prediction_results = {"Higher":[],"Lower":[]}

    while True:
        if LastRun >= interval:
            print(f"It has been {interval} number of seconds since last run. running now..")
            LastRun = 0
        else:
            print(f"Not been {interval} number of seconds since last run, it has been {LastRun}, sleeping for 5 minutes.")
            time.sleep(300)
            LastRun = LastRun + 300
            continue
 
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
        
        # UPDATE ALL LOG RECORDS WITH THE ACTUAL CLOSE, IF MISSING
        update_count = 0
        ignore_keys = ["LRPrediction","PredictedDirectionFromCurrent","CurrentPriceWhenPredicted"]
        for date in new_json_data:
            if date in json_file:
                for key in new_json_data[date]:
                    if key in ignore_keys:
                        continue
                    if new_json_data[date][key] != json_file[date][key]:
                        update_count += 1
                        print(f"Changing {key}: {json_file[date][key]} to {key}: {new_json_data[date][key]} for date {date} in log.")
                        json_file[date][key] = new_json_data[date][key]
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
        
        json_file[dt.datetime.strftime(next_interval,"%Y-%m-%d %H:%M:%S")] = {"close":"","prediction":"","LRPrediction":average,"PredictedDirectionFromCurrent":direction,"CurrentPriceWhenPredicted":current_price}

        with open(f"JSON\\{ticker}_{interval}_log.json","w")as f:
            json.dump(json_file,f,indent=2)
        