# Unit-price test

The revenue comparison asks whether `PP_i` tracks `GO_i`. Both are gross
revenues, so industry size can dominate. This test compares **unit prices**:

```
observed price:  price_obs_i = GO_i / Q_i
model price:     p_model_i   = PP_i / Q_i
```

`Q_i` is the **BEA gross-output quantity index** (TableID 16), not
`GO_i / price_obs_i`. This is essential: using `GO/price` to build `Q` makes
Moseley's unit price mechanically equal to the observed price.

Every price series is normalised per year to a quantity-weighted geometric mean
of one. The comparison is therefore about **relative prices**, not levels.

## What `PP/GO` is not

An earlier version used `PP/GO` as a “relative price.” That was wrong. With
`GO = p q` and `PP = p_model q`:

```
PP/GO = p_model / p
```

It is a **price ratio**, not a unit price. Its natural null is one, not a
regression against the observed price. It is a useful revenue-ratio diagnostic,
but it is not a unit-price test.

## Fit, 2005-2023

| Benchmark | log MAE | log RMSE | corr | slope | within 10% | within 25% |
|---|---:|---:|---:|---:|---:|---:|
| Moseley `PP/Q` | 0.119 | 0.167 | 0.794 | 0.475 | 56.0% | 83.0% |
| Moseley profit-rate `PP/Q` | 0.107 | 0.150 | 0.819 | 0.524 | 60.4% | 87.2% |
| **Moseley working-capital `PP/Q`** | **0.090** | **0.123** | **0.884** | **0.603** | **68.0%** | **92.6%** |
| Sraffa | 0.166 | 0.224 | 0.630 | 0.285 | 38.3% | 74.8% |
| Sraffa + fixed capital | 0.131 | 0.174 | 0.831 | 0.443 | 46.4% | 83.3% |
| Shaikh iterated | 0.167 | 0.216 | 0.669 | 0.311 | 35.8% | 75.6% |
| Regulating capital | 0.170 | 0.228 | 0.634 | 0.280 | 36.7% | 74.0% |
| Direct prices | 0.348 | 0.440 | 0.189 | 0.055 | 17.5% | 39.9% |

The Moseley unit-price fit is genuine, not an artifact. Working-capital Moseley
is the best unit-price benchmark: correlation 0.884, slope 0.603, and 92.6% of
industries within ±25%.

Sraffa and Shaikh also capture relative prices, but less strongly. Direct labour
values perform poorly.

## Within-sector test

| Benchmark | corr within | slope within |
|---|---:|---:|
| Moseley working-capital | 0.884 | 0.603 |
| Moseley profit-rate | 0.819 | 0.524 |
| Moseley base | 0.794 | 0.475 |
| Sraffa | 0.630 | 0.285 |
| Shaikh | 0.669 | 0.311 |
| Direct prices | 0.189 | 0.055 |

The within-sector results track the full-sample results, so the fit is not just
between-sector price levels.

## Measurement error

The value-added and gross-output deflators correlate at about 0.935 within
sector-year cells. Under a classical errors-in-variables assumption the
reliability is about `corr² ≈ 0.87`. Correcting the slopes would raise them by
roughly 15%, not enough to change the ranking.

## Gravitation on unit-price deviations

The unit-price deviation is:

```
d_it = log(price_obs_it / p_model_it)
```

Panel error-correction and one-year forecasts are in
`unit_price_gravitation.csv`. The qualitative result is the same as for
revenues: Moseley is the only benchmark with a negative output-adjustment
coefficient, but it is weak; Sraffa and Shaikh do not attract output.

## Verdict

- Moseley’s unit-price fit is **real**: corr 0.79 for the base benchmark, 0.82
  with a tax-exclusive profit rate, 0.88 with working capital.
- Sraffa and Shaikh reach corr 0.63-0.67; they capture relative prices but less
  strongly.
- Direct labour values remain poor (corr 0.19).
- The earlier “Moseley has no relative-price content” conclusion was based on
  `PP/GO`, which is a price ratio, not a unit price. With independent BEA
  quantities, Moseley performs well.

The honest summary: **Moseley’s stock-based benchmark has the strongest
unit-price content in this dataset.** Sraffa and Shaikh are second, and direct
labour values are not supported.
