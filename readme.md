# Poloniex Autotrading Bot
***I AM NOT RESPONSIBLE FOR ANY MONETARY LOSSES USING THIS BOT, THIS IS A CODING SIDE PROJECT AND NOTHING MORE, BY USING THIS BOT, YOU ARE ACCEPTING RESPONSIBILITY FOR ANY LOSSES YOU MAY INCUR.***

**This bot is designed to run _indefinitely_ unless one of the following things occurs:**
- You input an invalid Ticker when asked.
- You input an invalid Currency when asked.
- You input an invalid Interval to trade.
- You call an invalid API Command.
- Your Prediction_Iterations is not a multiple of 100.
- The account balance you are trying to AutoTrade is 0.
- You kill the script or container manually. **(Be Warned, This will not close open trades.)**

**Any invalid inputs/calls will error while returning a list of valid options.**

Once this repository has been cloned, there is some setup required before it can be used.

1. Rename APISettingsTEMPLATE.json to APISettings.json
2. Fill in the values of that JSON with your personal settings.
   1. Ticker: The Poloniex ticker code.
   2. Interval: The Interval you wish to trade in seconds.
   3. Prediction_Iterations: The amount of times you wish to predict using the model for, Must be a multiple of 100.
   4. Training_Iterations: The amount of times you wish to train the model for.
   5. AutoTrade: true will allow the bot to place trades if the criteria are met, false will run the bot without trading (good for testing predictions and backtesting).
   6. API_Secret: Your Poloniex API Secret.
   7. API_Key: Your Poloniex API Key.
3. There are two ways to run this bot: 
   1. Using the locally installed Python.
      - `pip install -r requirements.txt`
      - `python3 main.py`
   2. Or using the dockerfile.
      - To Build the docker image, `docker build -t poloniex-bot .`
      - Then to run the image, `docker run -it --rm poloniex-bot`
  
**This Bot does not support running multiple configs in one script.**

**If you wish to trade multiple Ticker/Interval combinations, Create a seperate copy of this repository with the desired settings.**
> Copyright of Ben Hiram Taylor