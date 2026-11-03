# Shaikh's real competition: the process, not the fixed point

Sraffa's prices of production are the fixed point; Shaikh's contribution is the
adjustment process around it. This page covers only the Shaikh-specific parts.
The fixed point itself is documented in `docs/sraffa.md`.

## Endogenous-`r` cost-plus iteration

```
c_k = p_k A + w l
r_k = (p_k y - c_k y) / (c_k y)
p_{k+1} = (1 + r_k) c_k
```

starting from labour values. On the current data it converges in **27 rounds on
average** (maximum 34, all years converged) with a residual below `1e-10`.

- Model-implied profit rate: **33.9%** average vs **30.3%** observed; 2023
  **35.7%** vs **33.8%**.
- The iterated prices are almost identical to the Sraffian fixed point:
  MAE **15.7%**, correlation **0.976**. Iteration adds convergence diagnostics
  and an implied rate, not a different price center.

## Cross-dual gravitation

A minimal price/output adjustment:

```
p_i' = p_i exp(-alpha (r_i - r_bar))
q_i' = q_i exp( beta  (r_i - r_bar))
```

Starting from labour values, weighted profit-rate dispersion falls from **0.146**
to approximately zero in about **199 steps**. This is a toy process; the full
stock-flow version is in `docs/stock_flow.md`.

## Stock-flow model

The state-space dataset (`p, q, k, I, u, w, l, A_t`) feeds a small stock-flow
simulation with price, output, investment, capital and wage adjustment. Its
current fit is: quantity RMSE 0.108 (corr 0.995), capital RMSE 0.237 (corr
0.976), investment RMSE 0.582, price RMSE 0.134 (corr 0.284). Output and capital
are well fitted; relative prices are not.

## Where Shaikh is and is not implemented

Implemented:

- labour values via the Leontief inverse;
- the endogenous-`r` cost-plus iteration;
- a toy cross-dual price/output adjustment;
- a first stock-flow cross-dual simulation.

Not implemented:

- regulating capitals (low-cost price leaders);
- firm entry, exit and cost heterogeneity;
- endogenous demand (consumption, investment demand, government, net exports);
- wage bargaining or a Phillips curve;
- financial constraints on investment;
- estimation with standard errors.

The Sraffian fixed point was previously labelled "Shaikh". That was incorrect:
solving `p = (1+r)(pA+wl)` once is Sraffa. Shaikh is the iteration and the
cross-dual process.
