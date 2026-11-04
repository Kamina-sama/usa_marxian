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

starting from labour values and using the deflated annual `A_t`. It converges in
**29 rounds on average** (maximum 34, all years converged) with a residual below
`1e-10`.

- Model-implied real profit rate: **38.7%** average vs **17.6%** observed real.
- The iterated prices are close to the Sraffian fixed point, but with the
  improved price data they fit worse: MAE **19.3%**, correlation **0.956**.
  Iteration adds convergence diagnostics and an implied rate, not a better
  price center.

## Regulating capitals (partial, key-gated)

Shaikh's prices are set by the lowest-cost "regulating" capitals, not the
average firm. Firm-level cost data are not keyless, so the project uses Census
Economic Census basic data (requires a free `CENSUS_API_KEY`):

```
unit_cost_sub = (payroll + materials) / receipts      # 6-digit NAICS
unit_cost_i   = weighted average within the IO industry
unit_cost_min = lowest sub-industry unit cost
factor_i      = 1 - theta * (1 - unit_cost_min / unit_cost_i)
PP_reg_i      = PP_Sraffa_i * factor_i
```

with `theta = 0.10`. The dispersion measure is the coefficient of variation of
6-digit unit costs within each IO industry. This is a sub-industry proxy, not a
firm-level distribution. Coverage is 60 of 65 market industries (1,140
observations); unmapped industries fall back to the Sraffa price.

Live result: `PP_reg` MAE 18.3%, RMSE 27.3%, corr 0.957, mean gap +0.0% —
slightly better than Sraffa's 18.6% MAE and essentially unbiased in aggregate.
Gravitation remains wrong-signed: `β_GO = +0.113` (p=0.008), `β_PP = +0.282`,
one-year forecast RMSE 0.263.

## Cross-dual gravitation

A minimal price/output adjustment:

```
p_i' = p_i exp(-alpha (r_i - r_bar))
q_i' = q_i exp( beta  (r_i - r_bar))
```

Starting from labour values, weighted profit-rate dispersion falls from **0.160**
to approximately zero in about **207 steps**. This is a toy process; the full
stock-flow version is in `docs/stock_flow.md`.

## Stock-flow model

The state-space dataset (`p, q, k, I, u, w, l, A_t`) feeds a small stock-flow
simulation with price, output, investment, capital and wage adjustment. Its
current fit is: quantity RMSE 0.095, capital RMSE 0.375, investment RMSE high,
price RMSE 0.302. Output is well fitted; capital and relative prices are not.

## Where Shaikh is and is not implemented

Implemented:

- labour values via the Leontief inverse, with FTE hours split by BLS
  manufacturing totals;
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
