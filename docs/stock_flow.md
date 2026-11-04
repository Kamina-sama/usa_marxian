# Stock-flow model

The state-space dataset provides, for 65 market industries and 1998-2023 (the
simulation itself runs 1999-2023 on the 63 industries with a complete series):

```
p_i  price index
q_i  real output (2017 dollars)
k_i  real capital stock
I_i  real investment
u_i  utilization
w_i  wage rate
l_i  labour coefficient
A_t  annual real input-output matrix
```

The stock-flow model is a small cross-dual system. It is a structural
exploration, not a full macroeconomic model.

## Demand closure

Final demand is parsed from the BEA Use table's final-use columns:

```
C_i  personal consumption
I_i  private fixed investment and inventory change
G_i  federal, state and local government
X_i  exports
M_i  imports
```

All components are deflated to 2017 dollars with the 71-industry gross-output
price index. Demand for industry `i` is:

```
D_i = sum_j A_ij q_j + C_i + I_i + G_i + X_i - M_i + residual_i
```

`I_i` is the **simulated** investment from the capital block, not the observed
Use-table investment. The residual is an explicit statistical/other term:

```
residual_i = q_i - sum_j A_ij q_j - C_i - G_i - X_i + M_i - I_i(observed)
```

It closes the observed base year. It is not a behavioural component and is
reported as a limitation.

## Behavioural block

```
cost_i   = (p A)_i + w l_i
r_i      = (p_i - cost_i) / cost_i
r_bar    = (p q - cost q) / (cost q)

p_i' = p_i exp(-alpha (r_i - r_bar))
q_i' = q_i + beta (D_i - q_i)
I_i  = depreciation_i + k_i [gamma0 + gamma1 (r_i - r_bar) + gamma2 (u_i - 1)]
k_i' = k_i - depreciation_i + I_i
w'   = w [1 + phi (U - 1)]
```

One-year output adjustment is bounded to `[0.5 q, 2.0 q]` so a noisy demand
component cannot drive an industry to extinction.

## Fit, 1999-2023

```
price       log RMSE 0.304   corr 0.319
quantity    log RMSE 0.196   corr 0.983
capital     log RMSE 0.352   corr 0.918
investment  log RMSE 0.495   corr 0.801
```

For comparison, the earlier exogenous-final-demand version fitted quantity at
0.108 and capital at 0.237, but it assumed away the demand side. Closing demand
makes the model structural and worsens the fit. That is the trade-off.

The weak dimension is still the price block. Output and capital track the data;
relative prices do not.

## Demand shocks

`simulate(..., demand_shock=..., shock_year=...)` adds a real-demand vector by
industry. This allows counterfactuals such as:

- a demand shock to one industry;
- a uniform demand boost;
- a negative import shock;
- comparing a demand shock with a price/cost shock.

The current model is suitable for direction-of-effect experiments, not for
quantitative policy analysis.

## Limitations

- The residual demand term is about 8% of output at the base year.
- Final demand is deflated with the industry gross-output price index, not
  component-specific consumption/investment deflators.
- Consumption, government, exports and imports are exogenous; only investment is
  simulated.
- Inventories are inside `k` but not modelled separately as a flow.
- Parameters are calibrated by a simple RMSE objective, not estimated with
  standard errors.
- The price block remains weak; cost pass-through alone does not fix it.

## Files

- `src/usa_marxian/model/stock_flow.py`
- `data/processed/state_space.csv`
- `data/processed/final_demand.csv`
- `output/tables/stock_flow_metrics.csv`
- `output/tables/stock_flow_trajectories.csv`
- `output/stock_flow.json`
