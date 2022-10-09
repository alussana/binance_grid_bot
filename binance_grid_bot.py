#!/usr/bin/env python

# binance_grid_bot.py

# Author: Alessandro Lussana <alussana@ebi.ac.uk>

import argparse as ap
import datetime
import json
import requests
from binance.client import Client
from binance import BinanceSocketManager

class GridBot:
    def __init__(self, key, secret, trade_pair = {'BTCUSDT': ['BTC', 'USDT']}):
        # user API authentication details
        self.key = key
        self.secret = secret
        # define tradeable pair and symbol
        self.trade_pair = trade_pair
        self.trade_symbol = list(trade_pair.keys())[0]
        self.trade_coin = self.trade_pair[self.trade_symbol][0]
        self.stake_currency = self.trade_pair[self.trade_symbol][1]
        # initialize client and socket manager
        self.client = Client(key, secret)
        #self.client = Client(key, secret, testnet=True)
        #client = await AsyncClient.create(api_key, api_secret)
        self.socket_manager = BinanceSocketManager(self.client)
        # initialize trade socket
        self.trade_socket = self.socket_manager.trade_socket(self.trade_symbol)
        # define price request url
        self.price_url = f'https://api.binance.com/api/v3/ticker/price?symbol={self.trade_symbol}'
        self.stake_balance = self.getFreeAssetBalance(self.stake_currency)
        # exchange parameters
        self.min_trade_amount = 0 # TODO
        # grid parameters
        self.grid_step = 0.001
        self.max_open_trades = 4
        self.sell_threshold = None
        self.buy_threshold = None
        self.trades_amount = []
        self.active_trades = 0
        self.tradeable_stake = 0.8
    def getFreeAssetBalance(self, asset: str) -> float:
        # TODO
        #return(float(self.client.get_asset_balance(asset=asset)['free']))
        return(100)
    def getPrice(self):
        response = requests.get(self.price_url).json()
        return(float(response['price']))
    def placeBuyOrder(self, price: float):
        # get time
        time = self.client.get_server_time()
        # get stake balance
        self.stake_balance = getFreeAssetBalance(self.trade_pair[self.trade_symbol][1])
        amount = self.stake_balance / self.max_open_trades * self.active_trades / self.buy_threshold 
        # TODO
        # get time
        time = self.client.get_server_time()
        local_time = datetime.datetime.now()
        self.trades_amount.append(amount)
        print(f'[{local_time}]: buy order placed for {amount} {self.trade_coin} triggered by buy threshold ({self.buy_threshold}) at Binance server time {time}.')
        self.active_trades += 1
        print(f'[{local_time}]: current active trades: {self.active_trades}')
    def placeSellOrder(self):
        # TODO
        # get time
        time = self.client.get_server_time()
        local_time = datetime.datetime.now()
        amount = self.trades_amount.pop()
        print(f'[{local_time}]: sell order placed for {amount} {self.trade_coin} triggered by sell threshold ({self.sell_threshold}) at Binance server time {time}.')
        self.active_trades -= 1
        print(f'[{local_time}]: current active trades: {self.active_trades}')
    def getMeanPrice(self):
        price = 0
        for i in range(10):
            price = price + self.getPrice()
        mean_price = price / 10
        return(mean_price)
    def start(self):
        local_time = datetime.datetime.now()
        print(f'[{local_time}]: starting bot.')
        mean_price = self.getMeanPrice()
        local_time = datetime.datetime.now()
        print(f'[{local_time}]: mean price for {self.trade_symbol} initialized at {mean_price}.')
        self.buy_threshold = mean_price * (1 - self.grid_step)
        self.sell_threshold = mean_price * (1 + self.grid_step)
        print(f'[{local_time}]: buy_threshold set at {self.buy_threshold}.')
        print(f'[{local_time}]: sell_threshold set at {self.sell_threshold}.')
        while True:
            try:
                price = self.getPrice()
                if self.active_trades > 0 and price > self.sell_threshold:
                    self.placeSellOrder()
                elif self.active_trades < self.max_open_trades and price < self.buy_threshold:
                    self.placeBuyOrder()
            except KeyboardInterrupt:
                local_time = datetime.datetime.now()
                print(f'[{local_time}]: bot terminated.')
                exit()
            except:
                local_time = datetime.datetime.now()
                print(f'[{local_time}]: cannot get current price; possible network issue.')

def parseArgs():
    parser = ap.ArgumentParser(description='Binance Grid Bot')
    requiredNamed = parser.add_argument_group('required named arguments')
    requiredNamed.add_argument(
        '--api_key', metavar='KEY', type=str, help='API key file path')
    requiredNamed.add_argument(
        '--api_secret', metavar='SECRET', type=str, help='API secret key file path')
    args = parser.parse_args()
    api_key = args.api_key
    api_secret = args.api_secret
    return(api_key, api_secret)

def readKeys(api_key, api_secret):
    with open(api_key) as api_key_fh:
        key = ''
        for line in api_key_fh:
            key = key + line.strip()
    with open(api_secret) as api_secret_fh:
        secret = ''
        for line in api_secret_fh:
            secret = secret + line.strip()
    return(key, secret)

def main():
    api_key, api_secret = parseArgs()
    key, secret = readKeys(api_key, api_secret)
    bot = GridBot(key, secret)
    bot.start()

def testBot():
    api_key = 'api_key'
    api_secret = 'api_secret_key'
    trade_pair = {'BTCUSDT': ['BTC', 'USDT']}
    key, secret = readKeys(api_key, api_secret)
    return(GridBot(key, secret))

if __name__ == '__main__':
    main()