import yfinance as yf 
import numpy as np 
import pandas as pd
from scipy import stats

positions = [
    {"symbol": "AAPL",  "quantity": 50},
    {"symbol": "MSFT",  "quantity": 30},
    {"symbol": "GOOGL", "quantity": 10},
    {"symbol": "JPM",   "quantity": 40},
    {"symbol": "XOM",   "quantity": 60},
]

portfolio_equity = 100000

def fetchprices(): # get prices of each stock in positions
    symbols = [p["symbol"] for p in positions]
    raw = yf.download(symbols, period = "1y", auto_adjust = True, progress = False)
    price = raw["Close"]
    return price

def computereturns(prices): #get daily returns
    returns = prices.pct_change()
    returns = returns.dropna()
    return returns

def ewmacov(returns): # uses EWMA to weigh older days less, builds then updates cov matrix each iteration, returns portfolio's total annual covariance
    lambda_ = 0.94
    cov = returns.cov() # come back to this later: figure out a better way for the seeding of this, the EWMA loop is recursive so need a better starting seed for it
    for i in range(1,len(returns)):
        r_yesterday = returns.iloc[i-1]
        cov = lambda_ * cov + (1 - lambda_) * np.outer(r_yesterday, r_yesterday)
    annual_cov = 252 * cov
    return annual_cov

def weights(positions, prices): # finds what weight each stock makes up in the portfolio
    quantity = pd.Series({p["symbol"] : p["quantity"] for p in positions})
    latest_prices = prices.iloc[-1]
    dollar_value = latest_prices * quantity
    weighted_value = dollar_value/dollar_value.sum()
    return weighted_value

def riskcontribution(positions): # risk contribution of each stock, its weight * sensitivity 
    prices = fetchprices()
    returns = computereturns(prices)

    cov = ewmacov(returns)
    w = weights(positions, prices)

    portfolio_var = w @ cov @ w 
    portfolio_vol = np.sqrt(portfolio_var)
    risk_contribution = {}
    risk_as_pct_portfolio_risk = {}
    w_times_cov = w @ cov
    for ticker in w.index:
        risk_contribution[ticker] = w[ticker] * w_times_cov[ticker] / portfolio_vol # risk contribution in vol units, a piece of portfolio vol not the % of it 
        risk_as_pct_portfolio_risk[ticker] = risk_contribution[ticker] / portfolio_vol * 100 # returns each stock's risk as a % of the entire portfolio's risk
    return pd.Series(risk_as_pct_portfolio_risk) 


# add a part that makes a dataframe with pos sizing as a % in one col, risk as a % of portfolio in another, stock tickers for rows 
# so you can see stock i is x% of portfolio position but y% of risk
def risk_vs_capital(positions):
    prices = fetchprices()
    w = weights(positions, prices)
    risk_pct = riskcontribution(positions)
    table = pd.DataFrame({
        "risk %" : risk_pct.round(2),  
        "capital %" : (w * 100).round(2)
    })
    table["gap"] = table["risk %"] - table["capital %"]
    return table

def portfolioexposure(positions, equity): # would need to define equity somewhere like positions is defined or pull from something like IBKR 
    prices = fetchprices()
    quantity = pd.Series({p["symbol"] : p["quantity"] for p in positions})
    latest_prices = prices.iloc[-1]
    dollar_value = latest_prices * quantity
    # gross exposure = (summation of abs(dollar position of stock i)) / account size
    gross_exp = dollar_value.abs().sum() / equity
    # net exposure = (summation of dollar pos of stock i) / account size 
    net_exp = dollar_value.sum() / equity
    return gross_exp, net_exp

def var_t(portfolio_vol_daily, portfolio_val, returns, confidence = 0.95):
    v = stats.t.fit(returns)[0]
    t_mult = stats.t.ppf(confidence, df=v) * np.sqrt((v -2) / v)
    VaR = t_mult * portfolio_vol_daily * portfolio_val 
    return VaR

def risk_concentration_limit(positions, threshold = 30):
    risk = riskcontribution(positions)
    breaches = []
    for ticker in risk.index:
        if risk[ticker] >= threshold:
            breaches.append(f"Breach: {ticker} is {risk[ticker]}% of portfolio risk. limit is {threshold}%")
    return breaches

def pos_size_limit(positions, prices, threshold = 0.2):
    w = weights(positions, prices)
    breaches = []
    for ticker in w:
        if w[ticker] >= threshold:
            breaches.append(f"Breach: {ticker} is over portfolio weight limit at {w[ticker]}")
    return breaches

def exposure_limit(dollar_values, equity, max_gross=1.0):
    gross = dollar_values.abs().sum() / equity
    if gross > max_gross:
        return f"Breach: gross exposure {gross*100:.0f}% exceeds limit of {max_gross*100:.0f}%"
    return None       

def var_limit(var_dollars, max_var_dollars=3000):
    if var_dollars > max_var_dollars:
        return f"Breach: 1-day VaR ${var_dollars:,.0f} exceeds limit ${max_var_dollars:,.0f}"
    return None
    
def check_limits(positions, dollar_values, equity, VaR):
    breaches = []
    breaches += risk_concentration_limit(positions, threshold=40)  
    breaches += [exposure_limit(dollar_values, equity, max_gross=1.0)]
    breaches += [var_limit(VaR, max_var_dollars=3000)]
    return [b for b in breaches if b is not None]

def main():
    prices = fetchprices()
    returns = computereturns(prices)
    cov = ewmacov(returns)
    vols = pd.Series(np.sqrt(np.diag(cov)), index=cov.columns)
    w = weights(positions, prices)

    portfolio_var = w @ cov @ w
    portfolio_vol = np.sqrt(portfolio_var)
    portfolio_vol_daily = portfolio_vol / np.sqrt(252)

    quantity = pd.Series({p["symbol"]: p["quantity"] for p in positions})
    dollar_values = prices.iloc[-1] * quantity               
    portfolio_value = dollar_values.sum()
    portfolio_returns = returns @ w

    VaR = var_t(portfolio_vol_daily, portfolio_value, portfolio_returns)

    print(f"Annual portfolio vol: {portfolio_vol*100:.1f}%")
    print(f"1-day 95% VaR: ${VaR:,.0f}")

    breaches = check_limits(positions, dollar_values, portfolio_equity, VaR)  
    print("\n".join(breaches) if breaches else "All limits OK.")


main()
   