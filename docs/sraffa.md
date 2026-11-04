# Sraffa's prices of production

This page describes the Sraffian component of the project and reports its
empirical result against the other benchmarks.

## What is Sraffian here

Sraffa's prices of production solve a simultaneous system with a uniform profit
rate on flow capital:

```
p = (1 + r)(p A + w l)
```

Relative prices are independent of `w`; the scale is fixed by normalising
`p . GO` to total gross output. In the code:

- `sraffa_prices_of_production(...)` — the direct solution of
  `p = w (1+r) l [I - (1+r) A]^-1`;
- `iterative_prices(...)` — the fixed-`r` cost-plus iteration, which converges
  to the same ray and is kept as a numerical check.

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
| Moseley `PP` | 12.4% | 19.4% | 0.983 | 1.043 | 89.5% | -5.7% |
| Sraffa `PP_Sraffa` | 18.7% | 28.2% | 0.957 | 0.941 | 76.0% | -2.9% |
| Sraffa + fixed capital | 17.5% | 38.8% | 0.913 | 0.971 | 84.7% | -6.4% |
| Shaikh iterated `PP_Shaikh` | 19.3% | 29.5% | 0.955 | 0.944 | 74.0% | -3.4% |
| Direct prices (labour values) | 36.5% | 47.9% | 0.888 | 0.872 | 43.3% | -8.7% |

Sraffa's benchmark carries the smaller aggregate bias than Moseley's
(-2.9% vs -5.7%), but Moseley has the lower RMSE, the better typical absolute
error, the higher rank correlation and the revenue slope closer to one.

## Gravitation, 1998-2023

| Benchmark | mean abs gap | half-life | GO beta | PP beta | 1y forecast RMSE |
|---|---:|---:|---:|---:|---:|
| Moseley `PP` | 12.4% | 2.2y | -0.163 (p=0.015) | +0.105 (p=0.035) | 0.213 |
| Sraffa `PP_Sraffa` | 18.4% | 4.0y | +0.097 (p=0.014) | +0.257 (p<0.001) | 0.253 |
| Shaikh iterated `PP_Shaikh` | 18.6% | 3.6y | +0.097 (p=0.007) | +0.271 (p<0.001) | 0.253 |
| Direct prices (labour values) | 35.4% | 4.4y | +0.081 (p=0.020) | +0.226 (p<0.001) | 0.451 |

Naive forecast RMSE is 0.120.

With annual `A_t` in constant prices and 71-industry prices, Sraffa's benchmark
does **not** attract market output. The output coefficient is positive and
significant (`+0.097`, p=0.014): high relative output predicts higher future
output, which is divergence, not gravitation. The model price adjusts toward the
observed price (`+0.257`).

## Verdict

- **Moseley** fits typical industry errors and forecasts better, and is the only
  benchmark with the gravitation-predicted negative output coefficient.
- **Sraffa** has lower aggregate bias but worse typical error; with the improved
  price data its output adjustment is positive, not negative.
- **Shaikh's iteration** converges to essentially the same center as Sraffa, so
  it does not change the fit conclusion.
- **Direct labour values** fit worst by a wide margin. Once labour hours are
  measured (FTE) rather than allocated by compensation, labour values are a
  poor empirical price predictor.

The Sraffian fixed point is a useful aggregate benchmark, not a center of
gravitation in this panel.
