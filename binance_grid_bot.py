#!/usr/bin/env python

# binance_grid_bot.py

# Author: Alessandro Lussana <alussana@ebi.ac.uk>

import argparse as ap
import datetime
import time
import requests
import sqlalchemy
import pandas as pd
import numpy as np
from binance.client import Client
from binance import BinanceSocketManager

class GridBot:

    def __init__(self, key, secret, trade_pair = {'BTCUSDT': ['BTC', 'USDT']}, test=True, enable_sql=False):
        
        # test mode
        self.test_mode = test

        # database of price history
        self.enable_sql = enable_sql
        self.timestep_count = -1

        # user API authentication details
        self.key = key
        self.secret = secret

        # define tradeable pair and symbol
        self.trade_pair = trade_pair
        self.trade_symbol = list(trade_pair.keys())[0]
        self.trade_coin = self.trade_pair[self.trade_symbol][0]
        self.stake_currency = self.trade_pair[self.trade_symbol][1]

        # initialize client and socket manager
        if self.test_mode:
            self.client = Client(key, secret, testnet=True)
        else:
            self.client = Client(key, secret)
            #client = await AsyncClient.create(api_key, api_secret)
        self.socket_manager = BinanceSocketManager(self.client)
        
        # initialize trade socket
        self.trade_socket = self.socket_manager.trade_socket(self.trade_symbol)
        
        # define price request url
        self.price_url = f'https://api.binance.com/api/v3/ticker/price?symbol={self.trade_symbol}'
        if self.test_mode:
            #self.stake_balance = 100
            self.stake_balance = None
        else:
            self.stake_balance = None
        
        # exchange parameters
        self.min_trade_amount = 0 # TODO
        self.min_quantity = self.getMinQty()
        self.step_size = self.getStepSize()
        self.ndecimal_precision = int(-np.log10(self.step_size))
        # TODO get trading fees
        
        # grid parameters
        self.grid_step = 0.005
        self.max_open_trades = 3
        self.sell_threshold = None
        self.buy_threshold = None
        self.trades_amount = [] # LIFO queue of active trades amounts
        self.trades_price = [] # prices corresponding to the the positions in self.trades_amount
        self.active_trades = 0  # number of active trades
        self.tradeable_stake = 0.2
        self.stoploss = self.grid_step * (self.max_open_trades + 1) # loss tolerance for a position before triggering sell order
        self.stoploss_price = -np.inf # price that will trigger the stoploss for the oldest position

        # current price        
        self.price = None

    def getStepSize(self):
        filters = self.client.get_symbol_info(self.trade_symbol)['filters']
        stepSize = float(filters[2]['stepSize'])
        return(stepSize)
    
    def getFreeAssetBalance(self, asset: str) -> float:

        return(float(self.client.get_asset_balance(asset=asset)['free']))
    
    def getPrice(self) -> float:

        response = requests.get(self.price_url).json()
        return(float(response['price']))

    def getMinQty(self) -> float:
        info = self.client.get_symbol_info(self.trade_symbol)
        minQty = float(info['filters'][2]['minQty'])
        return(minQty)

    def getServerTime(self):

        time = self.client.get_server_time()
        return(time['serverTime'])
    
    def getTradingFees(self) -> float:
        if self.test_mode:
            # the testnet key seems to be invalid when calling client.get_trade_fee()
            return(0)
        else:
            fees = self.client.get_trade_fee(symbol=self.trade_symbol)
            fee = fees # TODO get taker or maker commissions
            return(fee)

    def placeBuyOrder(self):

        # get stake balance
        self.stake_balance = self.getFreeAssetBalance(self.stake_currency)

        # determine the amount to buy
        total_stake = self.stake_balance
        for i in range(len(self.trades_amount)):
            total_stake = total_stake + self.trades_amount[i] * self.trades_price[i]
        stake_amount = total_stake * self.tradeable_stake / self.max_open_trades
        amount = round(stake_amount / self.buy_threshold, self.ndecimal_precision)

        # log
        print('---')
        local_time = datetime.datetime.now()
        print(f'[{local_time}]: placing buy order for {amount} {self.trade_coin} triggered by buy threshold ({self.buy_threshold}).')

        # perform buy order
        order = self.client.create_order(
            symbol=self.trade_symbol,
            side='BUY',
            type='MARKET',
            quantity=amount
        )

        # get time
        time = self.getServerTime()
        local_time = datetime.datetime.now()
            
        # TODO print order details
        #print()
        #print(order)
        #print()

        # add the amount to the LIFO queue of active trades amounts
        self.trades_amount.append(amount)

        # add the price to the LIFO queue of active trades prices
        self.trades_price.append(self.price)

        # move grid
        self.buy_threshold = round(self.price * (1 - self.grid_step), 5)
        self.sell_threshold = round(self.price * (1 + self.grid_step), 5)

        # update the amount of active trades
        self.active_trades += 1
        
        # set stoploss price if no older positions exist
        if self.active_trades == 1:
            self.stoploss_price = self.trades_price[0] * (1 - self.stoploss)

        # log
        print(f'[{local_time}]: buy order placed for {amount} {self.trade_coin} triggered by buy threshold ({self.buy_threshold}) at Binance server time {time}.')
        print(f'[{local_time}]: current stake balance: {self.stake_balance}')
        print(f'[{local_time}]: current active trades: {self.trades_amount}')
        print(f'[{local_time}]: buy_threshold set at {self.buy_threshold}. | sell_threshold set at {self.sell_threshold}.')
    
    def placeSellOrder(self):

        # determine the amount to sell from the LIFO queue of active trades
        amount = self.trades_amount.pop()

        # remove the position from the list of active trades prices
        buy_price = self.trades_price.pop()

        # log
        print('---')
        local_time = datetime.datetime.now()
        print(f'[{local_time}]: placing sell order for {amount} {self.trade_coin} triggered by sell threshold ({self.sell_threshold}).')

        # perform the sell order
        order = self.client.create_order(
            symbol=self.trade_symbol,
            side='SELL',
            type='MARKET',
            quantity=amount
        )

        # get time
        time = self.getServerTime()
        local_time = datetime.datetime.now()
            
        # TODO print order details
        #print()
        #print(order)
        #print()
            
        # move grid
        self.buy_threshold = round(self.price * (1 - self.grid_step), 5)
        self.sell_threshold = round(self.price * (1 + self.grid_step), 5)

        # update the number of active trades
        self.active_trades -= 1
        
        # log
        print(f'[{local_time}]: sell order placed for {amount} {self.trade_coin} triggered by sell threshold ({self.sell_threshold}) at Binance server time {time}.')
        print(f'[{local_time}]: buy price was {buy_price}; sell price is {self.price}')
        print(f'[{local_time}]: current stake balance: {self.stake_balance}')
        print(f'[{local_time}]: current active trades: {self.trades_amount}')
        print(f'[{local_time}]: buy_threshold set at {self.buy_threshold}. | sell_threshold set at {self.sell_threshold}.')
    
    def executeStoploss(self):

        # determine the amount to sell from the oldest active trade
        amount = self.trades_amount.pop(0)

        # log
        print('---')
        local_time = datetime.datetime.now()
        print(f'[{local_time}]: placing sell order for {amount} {self.trade_coin} triggered by stoploss threshold ({self.stoploss_price}).')

        # perform the sell order
        order = self.client.create_order(
            symbol=self.trade_symbol,
            side='SELL',
            type='MARKET',
            quantity=amount
        )

        # get time
        time = self.getServerTime()
        local_time = datetime.datetime.now()
   
        # TODO print order details
        #print()
        #print(order)
        #print()

        # update the amount of active trades
        self.active_trades -= 1

        # update stoploss trigger price
        if self.active_trades > 0:
            self.stoploss_price = self.trades_price[0] * (1 - self.stoploss)
        else:
            self.stoploss_price = -np.inf

        # log
        print(f'[{local_time}]: sell order placed for {amount} {self.trade_coin} triggered by stoploss ({self.stoploss_price}) at Binance server time {time}.')
        print(f'[{local_time}]: current stake balance: {self.stake_balance}')
        print(f'[{local_time}]: current active trades: {self.trades_amount}')

    def getMeanPrice(self):
        price = 0
        for i in range(10):
            time.sleep(1)
            price = price + self.getPrice()
        mean_price = round(price / 10, 5) 
        return(mean_price)
    
    def start(self):
        
        # log
        local_time = datetime.datetime.now()
        print('---')
        if self.test_mode:
            print(f'[{local_time}]: starting bot in test mode.')
        else:
            print(f'[{local_time}]: starting bot.')
        
        # get starting stake balance
        if self.test_mode:
            #
            self.stake_balance = self.getFreeAssetBalance(self.stake_currency)
        else:
            self.stake_balance = self.getFreeAssetBalance(self.stake_currency)

        # log
        local_time = datetime.datetime.now()
        print('---')
        print(f'[{local_time}]: starting stake balance is {self.stake_balance} {self.stake_currency}.')
        
        # SQL engine
        if self.enable_sql:
            self.sql_engine = sqlalchemy.create_engine(f'sqlite:///{self.trade_symbol}.db')
            local_time = datetime.datetime.now()
            print('---')
            print(f'[{local_time}]: SQL engine is enabled; database created in {self.trade_symbol}.db.')
        else:
            local_time = datetime.datetime.now()
            print(f'[{local_time}]: SQL engine not enabled.')
        
        # set the starting price
        mean_price = self.getMeanPrice()

        # set the starting grid thresholds
        self.buy_threshold = round(mean_price * (1 - self.grid_step), 5)
        self.sell_threshold = round(mean_price * (1 + self.grid_step), 5)

        # log
        local_time = datetime.datetime.now()
        print('---')
        print(f'[{local_time}]: mean price for {self.trade_symbol} initialized at {mean_price}.')
        print(f'[{local_time}]: buy_threshold set at {self.buy_threshold}.')
        print(f'[{local_time}]: sell_threshold set at {self.sell_threshold}.')
        print(f'[{local_time}]: trade starts.')

        # grid strategy loop
        while True:
            try:
                # loop every couple of seconds
                time.sleep(2)

                # track the time
                local_time = datetime.datetime.now()
                self.timestep_count += 1

                # get the current price, write to sql if enabled
                try:
                    self.price = self.getPrice()
                    if self.enable_sql:
                        df = pd.DataFrame({'local_time': local_time, 'price': self.price}, index=[self.timestep_count])
                except:
                    if self.enable_sql:
                        df = pd.DataFrame({'local_time': local_time, 'price': 'NA'}, index=[self.timestep_count])
                    print(f'[{local_time}]: cannot get current price; possible network issue.')

                if self.enable_sql:
                    df.to_sql(self.trade_symbol, self.sql_engine, if_exists='append', index=True)
                
                # decide whether to trigger a stoploss, place a sell/buy order, or do nothing
                if self.active_trades > 0 and self.price > self.sell_threshold:
                    self.placeSellOrder()
                elif self.active_trades > 0 and self.price < self.stoploss_price:
                    self.executeStoploss()
                elif self.active_trades < self.max_open_trades and self.price < self.buy_threshold:
                    self.placeBuyOrder()

            except KeyboardInterrupt:
                local_time = datetime.datetime.now()
                print(f'[{local_time}]: bot terminated.')
                exit()

def parseArgs():
    # ./binance_grid_bot.py --api_key api_key_testnet --api_secret api_secret_testnet
    parser = ap.ArgumentParser(description='Binance Grid Bot')
    requiredNamed = parser.add_argument_group('required named arguments')
    requiredNamed.add_argument(
        '-k', '--api_key', metavar='KEY', type=str, help='API key file path',
        required=True)
    requiredNamed.add_argument(
        '-s', '--api_secret', metavar='SECRET', type=str,
        help='API secret key file path', required=True)
    optional = parser.add_argument_group('optional arguments')
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
    #trade_pair = {'BTCUSDT': ['BTC', 'USDT']}
    #trade_pair = {'XMRBUSD': ['XMR', 'BUSD']}
    trade_pair = {'XRPBUSD': ['XRP', 'BUSD']}
    #trade_pair = {'BUSDUSDT': ['BUSD', 'USDT']}
    bot = GridBot(key, secret, trade_pair, test=True, enable_sql=True)
    bot.start()

if __name__ == '__main__':
    main()