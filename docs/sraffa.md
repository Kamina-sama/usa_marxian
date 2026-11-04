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

## Fit, 2005-2023, 65 market industries

| Benchmark | MAE | RMSE | corr | slope | within 25% | mean gap |
|---|---:|---:|---:|---:|---:|---:|
| Moseley `PP` | 12.4% | 19.4% | 0.983 | 1.043 | 89.5% | -5.7% |
| Sraffa `PP_Sraffa` | 18.7% | 27.9% | 0.959 | 0.942 | 74.9% | -3.1% |
| Shaikh iterated `PP_Shaikh` | 19.3% | 29.2% | 0.956 | 0.945 | 74.1% | -3.5% |
| Direct prices (labour values) | 37.2% | 48.9% | 0.888 | 0.871 | 42.9% | -9.3% |

Sraffa's benchmark has lower RMSE, smaller mean bias and a slope closer to one
than Moseley's. It does worse on typical absolute error and rank correlation.

## Gravitation, 1998-2023

| Benchmark | mean abs gap | half-life | GO beta | PP beta | 1y forecast RMSE |
|---|---:|---:|---:|---:|---:|
| Moseley `PP` | 12.4% | 2.2y | -0.163 (p=0.015) | +0.105 (p=0.035) | 0.213 |
| Sraffa `PP_Sraffa` | 18.2% | 3.9y | +0.103 (p=0.008) | +0.265 (p<0.001) | 0.250 |
| Shaikh iterated `PP_Shaikh` | 18.6% | 3.7y | +0.100 (p=0.006) | +0.272 (p<0.001) | 0.252 |
| Direct prices (labour values) | 35.8% | 4.5y | +0.083 (p=0.015) | +0.225 (p<0.001) | 0.454 |

Naive forecast RMSE is 0.120.

With annual `A_t` in constant prices and 71-industry prices, Sraffa's benchmark
does **not** attract market output. The output coefficient is positive and
significant (`+0.103`, p=0.008): high relative output predicts higher future
output, which is divergence, not gravitation. The model price adjusts toward the
observed price (`+0.265`).

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
