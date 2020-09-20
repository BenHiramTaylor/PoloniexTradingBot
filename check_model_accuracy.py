import json
import os

if __name__ == "__main__":
    with open('APISettings.json','r') as f:
        config = json.load(f)
    interval = config["Interval"]
    ticker = config["Ticker"]
    if not os.path.exists(f"JSON\\{ticker}_{interval}_trade_log.json"):
        print(f"There is no saved data to analyse with the ticker: {ticker} at the interval {interval}.")
    else:
        total_predictions = list()
        correct_predictions = list()
        trades_taken = list()
        correct_trades_taken = list()
        with open(f"JSON\\{ticker}_{interval}_trade_log.json","r") as f:
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

        if len(total_predictions) > 0:
            prediction_percentage = len(correct_predictions)/len(total_predictions)*100
        else:
            prediction_percentage = 0
            
        if len(trades_taken) > 0:
            taken_percentage = len(correct_trades_taken)/len(trades_taken)*100
        else:
            taken_percentage = 0
        print(f"Total number of correct predictions {len(correct_predictions)}/{len(total_predictions)} This is an overall accuracy of {prediction_percentage}%\nOut of this amount {len(trades_taken)} were taken and {len(correct_trades_taken)} of those were correct, this is an actual accuracy of {taken_percentage}%.")
            