# Stock-flow cross-dual simulation

This is the first behavioural layer built on the state space. It is a small
stock-flow model, not a full real-competition model.

## State and data

For each market industry-year:

```
p_i, q_i, k_i, I_i, u_i, w, l_i, A_t
```

Final demand is reconstructed from observed output and the real input matrix:

```
F_t = q_t - A_t q_t
```

and treated as exogenous. This means the simulation is a **dynamic accounting
and adjustment model**, not a complete demand system.

## Behavioural block

```
cost_i = (p A)_i + w l_i
r_i    = (p_i - cost_i) / cost_i
r_bar  = (p q - cost q) / (cost q)

p_i' = p_i [1 + kappa (cost_i/p_i - 1)] exp(-alpha (r_i - r_bar))
q_i' = q_i + beta (D_i - q_i),        D_i = (A q)_i + F_i
I_i  = k_i [gamma0 + gamma1 (r_i - r_bar) + gamma2 (u_i - 1)]
k_i' = k_i - depreciation_i + I_i
w'   = w [1 + phi (U - 1)]
```

where `U` is the output-weighted average utilization. Investment is clipped at
zero; prices, quantities and capital are clipped positive.

## Calibration

The parameters are calibrated by matching simulated and observed price, output
and capital paths over 2005-2023, using differential evolution. The objective is:

```
log RMSE(price) + log RMSE(quantity) + 0.5 log RMSE(capital)
```

Current parameters:

- `alpha = 0.0185` — price response to profit differentials
- `beta = 0.80` — output response to demand gaps
- `gamma0 = 0.125` — baseline investment rate
- `gamma1 = 0.04` — investment response to profit differentials
- `gamma2 = 0.50` — investment response to utilization
- `phi = 0.0` — wage response to utilization
- `kappa = 0.0` — cost pass-through

`beta` and `gamma2` are at their upper bounds. That is a warning: the model wants
faster output and investment adjustment than the bounds allow.

## Fit, 2005-2023

- **Price**: log RMSE **0.134**, MAE 0.105, correlation **0.284**
- **Quantity**: log RMSE **0.108**, MAE 0.076, correlation **0.995**
- **Capital**: log RMSE **0.237**, MAE 0.159, correlation **0.976**
- **Investment**: log RMSE **0.582**, MAE 0.372, correlation **0.729**

Output and capital are fitted well. Relative prices are not: the price block
captures only a small part of observed relative-price movement. That is the main
failure of the current model.

## What is still missing

- **Endogenous demand.** Final demand is exogenous. A complete model needs
  consumption, investment demand, government and net exports.
- **Price formation.** The cross-dual price rule is too weak. A full model needs
  cost-plus pricing with firm heterogeneity, regulating capitals and entry.
- **Wage dynamics.** `phi = 0`; wages are effectively exogenous. A wage Phillips
  curve or bargaining block is missing.
- **Firm heterogeneity.** The model uses one representative firm per industry.
- **Regulating capitals.** Prices are not set by low-cost producers.
- **Financial constraints.** Investment is not finance-constrained.
- **Estimation uncertainty.** Parameters are calibrated, not estimated with
  standard errors; `beta` and `gamma2` hit their bounds.

## Files

- `output/tables/stock_flow_metrics.csv`
- `output/tables/stock_flow_trajectories.csv`
- `output/stock_flow.json`

The simulation is deliberately reported as a first structural layer, not as a
finished model of Shaikh's real competition.
