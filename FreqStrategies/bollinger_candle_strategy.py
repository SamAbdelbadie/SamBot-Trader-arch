# --- Do not remove these libs ---
import numpy as np  # noqa
import pandas as pd  # noqa
from pandas import DataFrame  # noqa
from datetime import datetime  # noqa
from typing import Optional, Union  # noqa

from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter,
                                IStrategy, IntParameter)

# --------------------------------
# Add your lib to import here
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)
import os 
import talib.abstract as ta
import pandas_ta as pta
import freqtrade.vendor.qtpylib.indicators as qtpylib
# import finta as fta

class bollinger_candle_strategy(IStrategy):
    """
    This is a strategy template to get you started.
    More information in https://www.freqtrade.io/en/latest/strategy-customization/

    You can:
        :return: a Dataframe with all mandatory indicators for the strategies
    - Rename the class name (Do not forget to update class_name)
    - Add any methods you want to build your strategy
    - Add any lib you need to build your strategy

    You must keep:
    - the lib in the section "Do not remove these libs"
    - the methods: populate_indicators, populate_entry_trend, populate_exit_trend
    You should keep:
    - timeframe, minimal_roi, stoploss, trailing_*
    """
    # Strategy interface version - allow new iterations of the strategy interface.
    # Check the documentation or the Sample strategy to get the latest version.
    INTERFACE_VERSION = 3

    # Optimal timeframe for the strategy.
    timeframe = '15m'

    # Can this strategy go short?
    can_short: bool = False

    # Minimal ROI designed for the strategy.
    # This attribute will be overridden if the config file contains "minimal_roi".
    minimal_roi = {
        # "1840": -0.005,
        "2000": 0.003,
        "1440": 0.007,
        # "720": 0.008,
        # "360": 0.008,
        "0": 0.0085
    }

    # Optimal stoploss designed for the strategy.
    # This attribute will be overridden if the config file contains "stoploss".
    stoploss = -0.05

    # Trailing stoploss
    trailing_stop = False
    # trailing_only_offset_is_reached = False
    # trailing_stop_positive = 0.01
    # trailing_stop_positive_offset = 0.0  # Disabled / not configured

    # Run "populate_indicators()" only for new candle.
    process_only_new_candles = True

    # These values can be overridden in the config.
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 36

    # Strategy parameters
    buy_rsi = IntParameter(10, 40, default=30, space="buy")
    sell_rsi = IntParameter(60, 90, default=70, space="sell")
    bollinger_band_bandwidth = IntParameter(0.02, 0.04, default=0.03, space="buy")
    # Optional order type mapping.
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    # Optional order time in force.
    order_time_in_force = {
        'entry': 'gtc',
        'exit': 'gtc'
    }
    
    @property
    def plot_config(self):
        return {
            # Main plot indicators (Moving averages, ...)
            'main_plot': {
                'tema': {},
                'sar': {'color': 'white'},
            },
            'subplots': {
                # Subplots - each dict defines one additional plot
                "MACD": {
                    'macd': {'color': 'blue'},
                    'macdsignal': {'color': 'orange'},
                },
                "RSI": {
                    'rsi': {'color': 'red'},
                }
            }
        }

    def informative_pairs(self):
        """
        Define additional, informative pair/interval combinations to be cached from the exchange.
        These pair/interval combinations are non-tradeable, unless they are part
        of the whitelist as well.
        For more information, please consult the documentation
        :return: List of tuples in the format (pair, interval)
            Sample: return [("ETH/USDT", "5m"),
                            ("BTC/USDT", "15m"),
                            ]
        """
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adds several different TA indicators to the given DataFrame

        Performance Note: For the best performance be frugal on the number of indicators
        you are using. Let uncomment only the indicator you are using in your strategies
        or your hyperopt configuration, otherwise you will waste your memory and CPU usage.
        :param dataframe: Dataframe with data from the exchange
        :param metadata: Additional information, like the currently traded pair
        :return: a Dataframe with all mandatory indicators for the strategies
        """
        
        # Momentum Indicators
        # ------------------------------------
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=36)

        # # Bollinger Bands 
        bollinger = qtpylib.bollinger_bands(dataframe['close'], window=36, stds=2)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_upperband'] = bollinger['upper']
        dataframe['bb_mid'] = bollinger['mid']
        dataframe['bb_bandwidth'] = (dataframe['bb_upperband'] - dataframe['bb_lowerband']) / dataframe['bb_lowerband']
        
        # Candle Color

        dataframe['current_candle_color'] = np.where(dataframe['close'] >= dataframe['open'], 1, -1)
        dataframe['prev_candle_color'] = np.where(dataframe['close'].shift(1) >= dataframe['open'].shift(1), 1, -1)



        # df_bb = fta.BBANDS(dataframe, period=24)

        # df_bb.columns = ['BB_UPPER_12h', 'BB_MIDDLE_12h', 'BB_LOWER_12h']
        # df_bb = df_bb[['BB_LOWER_12h', 'BB_UPPER_12h']]
        # dataframe = dataframe.join(df_bb, how='outer')
        # dataframe['BB_bandwidth'] = (dataframe['BB_UPPER_12h'] - dataframe['BB_LOWER_12h']) / dataframe['BB_LOWER_12h']


        # Retrieve best bid and best ask from the orderbook
        # ------------------------------------
        """
        # first check if dataprovider is available
        if self.dp:
            if self.dp.runmode.value in ('live', 'dry_run'):
                ob = self.dp.orderbook(metadata['pair'], 1)
                dataframe['best_bid'] = ob['bids'][0][0]
                dataframe['best_ask'] = ob['asks'][0][0]
        """

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the entry signal for the given dataframe
        :param dataframe: DataFrame
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with entry columns populated
        """
        dataframe.loc[
            (
                (dataframe['close'].shift(2) <  dataframe['bb_lowerband'].shift(2)) &  # Guard: tema below BB middle
                (dataframe['close'] >=  dataframe['bb_lowerband']) &  # Guard: tema below BB middle
                (dataframe['rsi'] > 40) &
                # (dataframe['bb_bandwidth'] >  self.bollinger_band_bandwidth.value) &
                (dataframe['current_candle_color']==1 )&
                (dataframe['prev_candle_color']==-1 )&
                (dataframe['volume'] > 0)  # Make sure Volume is not 0
            ),
            'enter_long'] = 1
        # Uncomment to use shorts (Only used in futures/margin mode. Check the documentation for more info)
        # dataframe.loc[
        #     (
        #         (dataframe['close'].shift(1) >  dataframe['bb_upperband']) &  # Guard: tema below BB middle
        #         (dataframe['close'].shift(1) >  dataframe['bb_upperband']) &  # Guard: tema below BB middle
        #         (dataframe['close'] <=  dataframe['bb_upperband']) &  # Guard: tema below BB middle
        #         (dataframe['bb_bandwidth'] >  self.bollinger_band_bandwidth.value) &
        #         (dataframe['volume'] > 0)  # Make sure Volume is not 0
        #     ),
        #     'enter_short'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        print(dataframe)
        """
        Based on TA indicators, populates the exit signal for the given dataframe
        :param dataframe: DataFrame
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with exit columns populated
        """
        dataframe.loc[
            (
                (dataframe['rsi']>  55) &  # Guard: tema below BB middle
                (dataframe['close']>=  (dataframe['bb_mid'] * 1.001) ) &  # Guard: tema below BB middle
                (dataframe['current_candle_color']==-1 )&
                (dataframe['prev_candle_color']==1 )&
                (dataframe['volume'] > 0)  # Make sure Volume is not 0
            ),
            'exit_long'] = 1
        # Uncomment to use shorts (Only used in futures/margin mode. Check the documentation for more info)
        # dataframe.loc[
        #     (
        #         (dataframe['close'] <  dataframe['bb_mid']) &  # Guard: tema below BB middle
        #         (dataframe['volume'] > 0)  # Make sure Volume is not 0
        #     ),
        #     'exit_short'] = 1
        return dataframe
    
