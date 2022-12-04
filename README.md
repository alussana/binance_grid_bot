# binance_grid_bot

## TODO

* get minimum trade amount for the trade token (exchange parameter) and use it in `GridBot.placeBuyOrder()` and `GridBot.placeSellOrder()` logic
    * check if getMinQty() works correctly
* factor in the fees to compute the buy and sell thresholds when not in test mode
* use additional database table to store the bot parameters, enabling to resume a run
* make dash monitoring interface