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

    price_db_file = f'{symbol}_price.db'
    wallet_db_file = f'{symbol}_wallet.db'

    cnx_price = sqlite3.connect(price_db_file)
    cnx_wallet = sqlite3.connect(wallet_db_file)

    df_price = pd.read_sql_query("SELECT * from XRPBUSD", con=cnx_price)
    df_wallet = pd.read_sql_query("SELECT * from XRPBUSD", con=cnx_wallet)

    template = 'plotly_dark'

    # Create figure
    price_fig = make_subplots()

    # Add traces
    price_fig.add_trace(
       go.Scatter(x=df_price['local_time'], y=df_price['price'], name="price")
    )

    # Add figure title
    price_fig.update_layout(
        title_text="Price",
        template=template
    )

    # Set x-axis title
    price_fig.update_xaxes(title_text="local_time")

    # Set y-axis titles
    price_fig.update_yaxes(title_text="<b>XRPBSUD</b> price")
    
    app = Dash(__name__)

    app.layout = html.Div([
        html.H1('Binance Grid Bot'),
        html.H2('Full transactions history'),
        dcc.RadioItems(
            id='radio',
            options=['One axis', 'Two axis'],
            value='One axis'
        ),
        dcc.Graph(id="wallet_graph"),
        html.H2('Price history - last 10800 bot cycles'),
        dcc.Graph(id="price_graph",
                  figure=price_fig)
    ])

    @app.callback(
        Output("wallet_graph", "figure"), 
        Input("radio", "value"))
    def display_(radio_value):

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
        fig.update_xaxes(title_text="local_time")

        # Set y-axes titles
        if radio_value == 'Two axis':
            fig.update_yaxes(title_text="<b>BUSD</b> in wallet", secondary_y=False)
            fig.update_yaxes(title_text="<b>XRP</b> in wallet", secondary_y=True)
        else:
            fig.update_yaxes(title_text="amount in wallet", secondary_y=False)

        return fig

    app.run_server(
        debug=True,
        port=9050,
        host='0.0.0.0',
        use_reloader=True
    )