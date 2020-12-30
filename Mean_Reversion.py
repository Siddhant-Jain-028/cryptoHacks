import pandas as pd
import numpy as np
import pandas_datareader as pdr
from datetime import datetime, timedelta
import statsmodels.tsa.stattools as ts
from statsmodels.regression.rolling import RollingOLS
import statsmodels.api as sm
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_style('darkgrid')
import warnings
warnings.simplefilter('ignore')
import yfinance as yf
############################
yf.pdr_override()

instruent_1 = 'BTC-USD'
instruent_2 = 'BTC-INR'

startyear = 2016
startmonth = 1
startday = 1
start = datetime(startyear,startmonth,startday)
now = datetime.now()

df1 = pdr.get_data_yahoo(instruent_1,start,now).dropna()
df2 = pdr.get_data_yahoo(instruent_2,start,now).dropna()

## find intersection between two series, ensure same length to avoid BT
intersect = df1.index.intersection(df2.index)
df1 = df1.loc[intersect]
df2 = df2.loc[intersect]

# create a dataframe using adj. close prices from both series
df_test = pd.DataFrame(index=df1.index)
df_test['%s_close' % 'BTC-USD'.lower()] = df1['Adj Close']
df_test['%s_close' % 'BTC-INR'.lower()] = df2['Adj Close']
df_test = df_test.dropna()



###Setting parameters for OLS regression rolling
roll_beta_window = 10 
zscore_window = 15

# calculates rolling hedge ratio - this allows to dynamically adjust weights
# and to calculate spread in the testing sample 
# runs regression [y = beta * x], where beta is hedge ratio 
# calculates spread as [pair1 + (-beta) * pair2]
roll_fit = RollingOLS(df_test.iloc[:, 0], df_test.iloc[:, 1], window=roll_beta_window).fit()
df_test['roll_beta'] = -roll_fit.params 
df_test['test_spread'] = df_test.iloc[:, 0] + (df_test.iloc[:, 1] * df_test.roll_beta)

# calculates Z-score
meanSpread = df_test.test_spread.rolling(window=int(zscore_window)).mean()
stdSpread = df_test.test_spread.rolling(window=int(zscore_window)).std()
df_test['zScore'] = (df_test.test_spread-meanSpread)/stdSpread

###########################################################
#Mean Reversion Strategy:
 
# Go Long/Short when z-score reaches an entry threshold
# Exit when z-score decreases in absolute terms and reaches exit threshold

# calculate the “normalised” Z-Score of the spread, and set up a rule for entry and exit whereby 
# short trades are entered into if the Z-Score increases above 1.25, and exits when it drops below 0.25,
# and vice-versa for long trades.


entryZscore = 1.25
exitZscore = 0.25

# calculates when portfolio is LONG
df_test['long_entry'] = ((df_test.zScore < - entryZscore) & ( df_test.zScore.shift(1) > - entryZscore)) 
df_test['long_exit'] = ((df_test.zScore > - exitZscore) & (df_test.zScore.shift(1) < - exitZscore))  
df_test.loc[df_test['long_entry'],'pos_long'] = 1 
df_test.loc[df_test['long_exit'],'pos_long'] = 0 
df_test['pos_long'][0] = 0 
df_test['pos_long'] = df_test['pos_long'].fillna(method='pad')
# calculates when portfolio is SHORT
df_test['short_entry'] = ((df_test.zScore > entryZscore) & ( df_test.zScore.shift(1) < entryZscore))
df_test['short_exit'] = ((df_test.zScore < exitZscore) & (df_test.zScore.shift(1) > exitZscore))
df_test.loc[df_test['short_entry'],'pos_short'] = -1
df_test.loc[df_test['short_exit'],'pos_short'] = 0
df_test['pos_short'][0] = 0
df_test['pos_short'] = df_test['pos_short'].fillna(method='pad')
    
# combines longs/shorts and remove Look ahead bias by lagging the signal
df_test['position'] = df_test['pos_long'].shift(1) + df_test['pos_short'].shift(1)

# recalculation
df_test['long_entry'] = ((df_test.pos_long.shift(1) == 1) & ((df_test.position - df_test.position.shift(1)) == 1)) 
df_test['long_exit'] = ((df_test.long_exit == True) & (df_test.position == 1))
df_test['short_entry'] = ((df_test.pos_short.shift(1) == -1)  & ((df_test.position - df_test.position.shift(1)) == -1))
df_test['short_exit'] = ((df_test.short_exit == True) & (df_test.position == -1))

# calculates adjusted spread using using current prices and hedge ratio from previous bar (avoiding look-ahead bias)
df_test['test_spread_adj'] = df_test.iloc[:, 0] + (df_test['roll_beta'].shift(1) * df_test.iloc[:, 1])

# calculates pct returns assuming you are always long
df_test['pct_ret'] = ((df_test['test_spread_adj'] - df_test['test_spread'].shift(1)) / 
                    (df_test.iloc[:, 0].shift(1) + (abs(df_test['roll_beta'].shift(1)) * df_test.iloc[:, 1].shift(1))))

# your actual portfolio return for that day according to your position
df_test['port_ret'] = df_test['position'] * df_test['pct_ret'] 
df_test['port_ret'].fillna(0.0, inplace=True)

# trading fees (set here as 0.1%: - slippage + transaction fees, for example you pay 1 USD per 1,000 value of trade
tr_costs = 0.001
df_test['tr_cost_paid'] = (df_test.long_entry | df_test.long_exit | df_test.short_entry | df_test.short_exit)
df_test['port_ret_net'] = df_test['port_ret'] - ( tr_costs * df_test['tr_cost_paid'])

# culmulative porfolio return gross and net
df_test['cum_port_ret'] = (df_test['port_ret'] + 1.0).cumprod()
df_test['cum_port_ret_net'] = (df_test['port_ret_net'] + 1.0).cumprod()

# HELPER FIGURES
# calculate average and std_dev of your actual returns (skip zeros)
mean = df_test.query("position == 1 or position  == -1")['port_ret'].mean()
std = df_test.query("position == 1 or position  == -1")['port_ret'].std()
mean_net = df_test.query("position == 1 or position  == -1")['port_ret_net'].mean()
std_net = df_test.query("position == 1 or position  == -1")['port_ret_net'].std()

# calculates how many days your portfolio hold any positions (is fully invested)
num_days_in_the_market = len(df_test.query("position == 1 or position  == -1")['port_ret'])

# calculate sum of long and short entries
num_trades_long = df_test.query('long_entry == True')['long_entry'].sum()
num_trades_short = df_test.query('short_entry == True')['short_entry'].sum()

# calculate total trading costs paid
approx_tr_costs = (num_trades_long + num_trades_short) * tr_costs

'''Since the strategy isn't always fully invested, we skip 'zero retun days' in calculating Sharpe Ratio and CAGR.
To adjust this SR ratio, you have to decide what you're going to do with that capital when you're not invested'''

# PERFORMANCE STATS (gross - no trading costs included)
# calculates Sharpe Ratio, Total Return and CAGR
ir = (mean / std) * np.sqrt(252)
cum_return = df_test['cum_port_ret'].iloc[-1] - 1.0
comp_ann_return = ((df_test['cum_port_ret'].iloc[-1] / df_test['cum_port_ret'].iloc[0]) ** (1 / (num_days_in_the_market / 365) ) ) - 1.0

# PERFORMANCE STATS (net - trading costs included)
ir_net = (mean_net / std_net) * np.sqrt(252)
cum_return_net = df_test['cum_port_ret_net'].iloc[-1] - 1.0
comp_ann_return_net = ((df_test['cum_port_ret_net'].iloc[-1] / df_test['cum_port_ret_net'].iloc[0]) ** (1 / (num_days_in_the_market / 365) ) ) - 1.0


# Print performance statistics
print(f'# BACKTEST PERFORMANCE GROSS #')
print(f'+ Ann. Information Ratio : {round(ir, 2)}')
print(f'+ Cumulative Return      : {round(cum_return,3)}')
print(f'+ Cum Annual Growth Rate : {round(comp_ann_return, 3)}')
print(f'+ Average Return         : {round(mean, 4)}')
print(f'+ Standard Deviation     : {round(std,4)}')
print()
print(f'# BACKTEST PERFORMANCE NET #')
print(f'+ Ann. Information Ratio : {round(ir_net, 2)}')
print(f'+ Cumulative Return      : {round(cum_return_net,3)}')
print(f'+ Cum Annual Growth Rate : {round(comp_ann_return_net, 3)}')
print(f'+ Average Return         : {round(mean_net, 4)}')
print(f'+ Standard Deviation     : {round(std_net,4)}')
print()
print(f'# OTHER BACKTEST METRICS #')
print(f'+ Num Long Entries       : {num_trades_long}')
print(f'+ Num Short Entries      : {num_trades_short}')
print(f'+ Days in the market     : {num_days_in_the_market}')
print(f'+ Total fees paid        : {round(approx_tr_costs, 4)}')


