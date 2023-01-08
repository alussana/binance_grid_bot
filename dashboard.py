#!/usr/bin/env python

# binance_grid_bot_dashboard.py

# Author: Alessandro Lussana <alussana@ebi.ac.uk>

from dash import Dash, html, dcc
import plotly.express as px
import plotly.io as pio
import pandas as pd
import sqlite3
import argparse as ap
from dash import Dash, dcc, html, Input, Output
from plotly.subplots import make_subplots
import plotly.graph_objects as go

def parseArgs():
    # ./binance_grid_bot_dashboard.py --symbol XRPBUSD
    parser = ap.ArgumentParser(description='Binance Grid Bot Dashboard')
    requiredNamed = parser.add_argument_group('required named arguments')
    requiredNamed.add_argument(
        '--symbol', metavar='SYMBOL', type=str,
        help='traded pair symbol',
        required=True)
    optional = parser.add_argument_group('optional arguments')
    args = parser.parse_args()
    symbol = args.symbol
    return(symbol)

if __name__ == '__main__':
    symbol = parseArgs()

    wallet_db_file = f'{symbol}_wallet.db'

    cnx_wallet = sqlite3.connect(wallet_db_file)

    df_wallet = pd.read_sql_query("SELECT * from XRPBUSD", con=cnx_wallet)

    template = 'plotly_dark'

    # calculate unrealized profit at each timepoint
    start_stake_amount = float(df_wallet.loc[df_wallet['index']==-1, 'BUSD'])
    start_trade_amount = float(df_wallet.loc[df_wallet['index']==-1, 'XRP'])
    unrealized_profit = [0]
    unrealized_profit_percent = [0]
    for timepoint in df_wallet['local_time'][1:]:
        stake_amount = float(df_wallet.loc[df_wallet['local_time']==timepoint]['BUSD'])
        trade_amount = float(df_wallet.loc[df_wallet['local_time']==timepoint]['XRP'])
        price = float(df_wallet.loc[df_wallet['local_time']==timepoint]['XRPBUSD_price'])
        stake_delta = stake_amount - start_stake_amount
        trade_delta = trade_amount - start_trade_amount
        delta_profit = stake_delta + trade_delta * price
        unrealized_profit.append(delta_profit)
        unrealized_profit_percent.append(delta_profit / start_stake_amount * 100)
    df_profit = pd.DataFrame({
        'local_time':df_wallet['local_time'],
        'unrealized_profit': unrealized_profit,
        'unrealized_profit_percent': unrealized_profit_percent
        })
    
    app = Dash(__name__)

    app.layout = html.Div([
        html.H1('Binance Grid Bot'),
        html.H2('Full transactions history'),
        dcc.RadioItems(
            id='radio_wallet',
            options=['One axis', 'Two axis'],
            value='One axis'
        ),
        dcc.Graph(id="wallet_graph"),
        html.H2('Unrealized profit history'),
        dcc.RadioItems(
            id='radio_profits',
            options=['Absolute', 'Percentage'],
            value='Absolute'
        ),
        dcc.Graph(id="profit_graph")
    ])

    @app.callback(
        Output("wallet_graph", "figure"), 
        Input('radio_wallet', "value"))
    def display_trades(radio_value):

        # Create figure with secondary y-axis
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Add traces
        fig.add_trace(
            go.Scatter(x=df_wallet['local_time'], y=df_wallet['BUSD'], name="BUSD"),
            secondary_y=False
        )

        fig.add_trace(
            go.Scatter(x=df_wallet['local_time'], y=df_wallet['XRP'], name="XRP"),
            secondary_y = radio_value == 'Two axis'
        )

        # Add figure title
        fig.update_layout(
            title_text="Wallet",
            template=template
        )

        # Set x-axis title
        fig.update_xaxes(title_text="local time")

        # Set y-axes titles
        if radio_value == 'Two axis':
            fig.update_yaxes(title_text="<b>BUSD</b> in wallet", secondary_y=False)
            fig.update_yaxes(title_text="<b>XRP</b> in wallet", secondary_y=True)
        else:
            fig.update_yaxes(title_text="amount in wallet", secondary_y=False)

        return fig

    @app.callback(
        Output("profit_graph", "figure"), 
        Input('radio_profits', "value"))
    def display_profits(radio_value):

        fig = make_subplots()

        if radio_value == 'Absolute':
            column='unrealized_profit'
            title='Unrealized profit'
            y_label='unrealized profit in BUSD'
        elif radio_value == 'Percentage':
            column='unrealized_profit_percent'
            title='Unrealized profit (%)'
            y_label='unrealized profit (%) in BUSD'

        fig.add_trace(
            go.Scatter(x=df_profit['local_time'], y=df_profit[column], name="Profit")
        )
        fig.update_layout(
            title_text=title,
            template=template
        )
        fig.update_xaxes(title_text="local time")
        fig.update_yaxes(title_text=y_label)

        return(fig)

    app.run_server(
        debug=True,
        port=9050,
        host='0.0.0.0',
        use_reloader=True
    )