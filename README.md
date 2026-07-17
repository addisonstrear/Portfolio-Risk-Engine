# Portfolio-Risk-Engine
reports the volatility of the portfolio, attributes that volatility to individual positions, estimates a one day loss figure, and checks the book against a set of predefined limits.


### Overview:
 
Given a set of positions and an account's equity, the engine performs the following steps:
 
1. Downloads one year of adjusted closing prices and builds a daily return series.
2. Estimates a covariance matrix using an exponentially weighted scheme, so recent observations are weighted more heavily than older ones.
3. Computes annualized portfolio volatility.
4. Decomposes volatility into a per position contribution, identifying which holdings are driving the risk.
5. Compares each position's share of risk against its share of capital.
6. Estimates a one day Value at Risk using Student t distribution.
7. Evaluates the book against a set of risk limits and reports any breaches.

### Methodology:
 
### Covariance estimation
 
The covariance matrix is estimated using an EWMA update in the RiskMetrics tradition, which weights recent returns more heavily and lets the estimate respond to changing market conditions:
 
```
Sigma_t = lambda * Sigma_{t-1} + (1 - lambda) * r_{t-1} r_{t-1}',   lambda = 0.94
```
 
The loop seeds with the sample covariance and updates forward one day at a time. The final matrix is annualized by a factor of 252.
 
### Position weights
 
Each weight is the dollar value of the position over the total value of the book:
 
```
w_i = (P_i * q_i) / sum_j (P_j * q_j)
```
 
where P_i is the latest price and q_i the number of shares. The current implementation assumes a long only book.
 
### Portfolio volatility
 
```
sigma_p = sqrt( w' Sigma w )
```
 
### Risk attribution
 
Volatility is attributed to each position through its component contribution to portfolio risk:
 
```
RC_i = w_i * (Sigma w)_i / sigma_p,    with   sum_i RC_i = sigma_p
```
 
Contributions are reported as a percentage of total risk and therefore sum to 100. The value of this is in the comparison with capital weight. A position may represent 15 percent of the book by dollars but account for 30 percent of its risk, so the `risk_vs_capital` table is built to show this through risk percentage, capital percentage, and the gap between them.
 
### Value at Risk
 
One day VaR is computed from a Student t distribution rather than a normal, since daily equity returns exhibit heavier tails than the normal assumption permits. The degrees of freedom are fit to the portfolio return series, the resulting quantile is rescaled to unit variance, and it is then applied to the daily portfolio volatility and the dollar value of the book:
 
```
VaR = t_inv(alpha, nu) * sqrt((nu - 2) / nu) * sigma_daily * V,   alpha = 0.95
```
 
The rescaling factor is necessary because a Student t with nu degrees of freedom has variance nu / (nu - 2). Without it the quantile would not be expressed in standard deviation units, which is the unit that sigma_daily carries. THe EWMA estimate provides the scale and the fitted t supplies the tail shape.
 
### Exposure
 
```
gross = sum_i |D_i| / E
net   = sum_i  D_i  / E
```
 
where D_i is the dollar value of position i and E is account equity.
 
### Limits
 
The checks are kept independent so that thresholds can be adjusted individually:
 
- Risk concentration. Flags any position above a given share of total risk. The main routine applies this at 40 percent.
- Position size. Flags any weight above 20 percent. Implemented but not currently included in the main limit check.
- Gross exposure. Flags gross exposure above 100 percent of equity.
- Value at Risk. Flags one day VaR above a fixed dollar threshold, set at 3,000 in the main routine.
`check_limits` runs the concentration, exposure, and VaR checks together and returns any that breach. The main routine prints annual portfolio volatility, the one day 95 percent VaR, and the resulting breaches, or confirms that all limits are satisfied.
 
 
Sample output:
 
```
Annual portfolio vol: 18.4%
1-day 95% VaR: $2,150
All limits OK.
```
 
The figures above are illustrative and depend on the prices retrieved on the day of the run.
 
### What's left to do:
 
The pipeline is largely complete but has not yet been confirmed running end to end using a live book instead of a fixed sample. Outstanding items:
 
- EWMA seed. The update is seeded with the full sample covariance, which slightly affects later information in the initial estimate. A cleaner seed would be ideal 
