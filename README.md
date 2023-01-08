# binance_grid_bot

## setup virtual environment

```
python3 -m venv env
source env/bin/activate
pip install python-binance
pip install pandas
pip install dash
```

## example usage

### start the bot [tmp]

```
./bot.py --api_key testnet_api_key --api_secret testnet_secret_key
```

### deploy Dash interface [tmp]

```
./dashboard.py --symbol XRPBUSD
```

## to do

* make testnet mode triggerable from command arguments
* add generic exceptions handling
* automatically handle currency names in dash monitoring interface from arguments
* factor in the fees to compute the buy and sell thresholds when not in test mode
* use additional database table to store the bot parameters, enabling to resume a run
