import json
import os

if __name__ == "__main__":
    with open('APISettings.json','r') as f:
        config = json.load(f)
    interval = config["Interval"]
    ticker = config["Ticker"]
    if not os.path.exists(f"JSON\\{ticker}_{interval}_log.json"):
        print(f"There is no saved data to analyse with the ticker: {ticker} at the interval {interval}.")
    else:
        total_predictions = list()
        correct_predictions = list()
        trades_taken = list()
        correct_trades_taken = list()
        with open(f"JSON\\{ticker}_{interval}_log.json","r") as f:
            data = json.load(f)

        for period in data:
            if "correct_prediction" not in data[period]:
                continue

            if data[period]["correct_prediction"]:
                correct_predictions.append(1)

            total_predictions.append(1)

            if data[period]["predicted_direction_from_current"] == "Higher":
                difference = data[period]["prediction"] - data[period]["previous_close"]
            else:
                difference = data[period]["previous_close"] - data[period]["prediction"]

            if difference > 5:
                trades_taken.append(1)
                if data[period]["correct_prediction"]:
                    correct_trades_taken.append(1)

        print(f"Total number of correct predictions {len(correct_predictions)}/{len(total_predictions)}, out of this amount {len(trades_taken)} were taken and {len(correct_trades_taken)} of those were correct.")
            