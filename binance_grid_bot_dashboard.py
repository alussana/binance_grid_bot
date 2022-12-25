#!/usr/bin/env python

# binance_grid_bot_dashboard.py

# Author: Alessandro Lussana <alussana@ebi.ac.uk>

from dash import Dash, html, dcc
import plotly.express as px
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
    
    app = Dash(__name__)

    app.layout = html.Div([
        html.H4('Interactive data-scaling using the secondary axis'),
        html.P("Select red line's Y-axis:"),
        dcc.RadioItems(
            id='radio',
            options=['Primary', 'Secondary'],
            value='Secondary'
        ),
        dcc.Graph(id="graph"),
    ])


    @app.callback(
        Output("graph", "figure"), 
        Input("radio", "value"))
    def display_(radio_value):

        # Create figure with secondary y-axis
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Add traces
        fig.add_trace(
            go.Scatter(x=df_wallet['local_time'], y=df_wallet['BUSD'], name="BUSD"),
            secondary_y=False,
        )

        fig.add_trace(
            go.Scatter(x=df_wallet['local_time'], y=df_wallet['XRP'], name="XRP"),
            secondary_y=True,
        )

        # Add figure title
        fig.update_layout(
            title_text="Wallet"
        )

        # Set x-axis title
        fig.update_xaxes(title_text="local time (Rome)")

        # Set y-axes titles
        fig.update_yaxes(title_text="<b>BUSD</b> in wallet", secondary_y=False)
        fig.update_yaxes(title_text="<b>XRP</b> in wallet", secondary_y=True)

        return fig


    app.run_server(
        debug=True,
        port=9050,
        host='0.0.0.0'
    )