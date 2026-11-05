# Sraffa's prices of production

This page describes the Sraffian component of the project and reports its
empirical result against the other benchmarks.

## What is Sraffian here

Sraffa's prices of production solve a simultaneous system with a uniform profit
rate, industry-specific wage costs and depreciation as a cost:

```
p = (1 + r)(p A + v + d)
```

so that `p = (1+r)(v + d)[I - (1+r)A]^-1`, where `v_j = V_j/q_j` is wage cost per
unit of real output and `d_j = CFC_j/q_j` is consumption of fixed capital per
unit. Relative prices are independent of the wage level; the scale is fixed by
normalising to total output.

Two choices are worth naming. **Wage rates are industry-specific**, because
`V_j/q_j` embeds each industry's own wage level; Sraffa's system has a single
wage. This is an empirical convention, not a theoretical one, and it means part
of the benchmark's fit comes from reproducing observed wage differentials.
**Depreciation enters as a marked-up cost**, which is the standard treatment when
the capital matrix is absent. It is conservative relative to the joint-product
model below, where profit is charged on the whole stock, `B(r + delta)`.

In the code:

- `sraffa_prices_of_production(...)` — the direct solution, with optional
  `depreciation_cost`;
- `iterative_prices(...)` — the fixed-`r` cost-plus iteration on the same cost
  base, kept as a numerical check that the two agree on one ray;
- `sraffa_prices_fixed_capital(...)` — Sraffa's joint-production treatment,
  `p[I - (1+r)A - B(r + Delta)] = (1+r)v`.

`A` is the **deflated** annual Use matrix (2017 dollars), and `l` is direct
labour per 2017 dollar of output. Industry labour hours are measured from BEA
Table 6.5D full-time-equivalent employees scaled to macro hours; the labour
values `lambda = l (I - A)^-1` are classical direct prices.

## Why this is not "Shaikh"

Shaikh's prices of production share the same fixed-point algebra, but his
distinctive claim is the **adjustment process** — real competition, capital
flows, entry and turbulent gravitation (see `docs/shaikh.md`). Solving the
fixed point once is Sraffa.

## Fit, 1998-2023, 60 market industries

| Benchmark | MAE | RMSE | corr | slope | within 25% | mean gap |
|---|---:|---:|---:|---:|---:|---:|
| Moseley `PP` (working capital) | 10.4% | 13.2% | 0.991 | 1.035 | 94.2% | -4.4% |
| Sraffa `PP_Sraffa` | 16.5% | 24.5% | 0.968 | 0.987 | 84.0% | -5.1% |
| Sraffa + fixed capital | 17.5% | 38.8% | 0.913 | 0.971 | 84.7% | -6.4% |
| Shaikh iterated `PP_Shaikh` | 17.8% | 26.6% | 0.962 | 0.980 | 78.8% | -5.2% |
| Direct prices (labour values) | 36.5% | 47.9% | 0.888 | 0.872 | 43.3% | -8.7% |

Moseley's benchmark is ahead on every criterion: lower typical error, lower
RMSE, a mean gap closer to zero, higher rank correlation and a revenue slope
closer to one. Sraffa's fit improves substantially once depreciation is in its
cost base — MAE falls from 18.7% to 16.5% and the revenue slope rises from 0.941
to 0.987 — but the ordering does not change.

## Gravitation, 1998-2023

| Benchmark | mean abs gap | half-life | GO beta | PP beta | 1y forecast RMSE |
|---|---:|---:|---:|---:|---:|
| Moseley `PP` (working capital) | 10.4% | 2.0y | -0.091 (p=0.239) | +0.201 (p=0.004) | 0.176 |
| Sraffa `PP_Sraffa` | 15.2% | 5.8y | +0.107 (p=0.008) | +0.220 (p<0.001) | 0.206 |
| Shaikh iterated `PP_Shaikh` | 16.3% | 5.1y | +0.111 (p=0.006) | +0.237 (p<0.001) | 0.214 |
| Direct prices (labour values) | 35.4% | 4.4y | +0.081 (p=0.020) | +0.226 (p<0.001) | 0.451 |

Naive forecast RMSE is 0.120.

With annual `A_t` in constant prices and 71-industry prices, Sraffa's benchmark
does **not** attract market output. The output coefficient is positive and
significant (`+0.107`, p=0.008): high relative output predicts higher future
output, which is divergence, not gravitation. The model price adjusts toward the
observed price (`+0.220`).

## Verdict

- **Moseley** fits typical industry errors and forecasts better, and is the only
  benchmark whose output coefficient carries the gravitation-predicted negative
  sign — though on the working-capital variant it is not significant (p=0.239).
- **Sraffa** has lower aggregate bias but worse typical error; with the improved
  price data its output adjustment is positive, not negative.
- **Shaikh's iteration** converges to essentially the same center as Sraffa, so
  it does not change the fit conclusion.
- **Direct labour values** fit worst by a wide margin. Once labour hours are
  measured (FTE) rather than allocated by compensation, labour values are a
  poor empirical price predictor.

The Sraffian fixed point is a useful aggregate benchmark, not a center of
gravitation in this panel.
