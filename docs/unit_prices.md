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

## Fit, 1998-2023, 60 market industries

| Benchmark | log MAE | log RMSE | corr | slope | within 10% | within 25% |
|---|---:|---:|---:|---:|---:|---:|
| Moseley `PP/Q` | 0.119 | 0.167 | 0.794 | 0.475 | 56.0% | 83.0% |
| Moseley profit-rate `PP/Q` | 0.107 | 0.150 | 0.819 | 0.524 | 60.4% | 87.2% |
| **Moseley working-capital `PP/Q`** | **0.090** | **0.123** | **0.884** | **0.603** | **68.0%** | **92.6%** |
| Sraffa | 0.166 | 0.224 | 0.630 | 0.285 | 38.3% | 74.8% |
| Sraffa + fixed capital | 0.131 | 0.174 | 0.831 | 0.443 | 46.4% | 83.3% |
| Shaikh iterated | 0.167 | 0.216 | 0.669 | 0.311 | 35.8% | 75.6% |
| Shaikh + fixed capital | 0.152 | 0.204 | 0.806 | 0.370 | 39.5% | 79.1% |
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
| Moseley | 0.774 | 0.608 |
| Sraffa | 0.588 | 0.387 |
| Shaikh | 0.606 | 0.420 |
| Regulating | 0.586 | 0.378 |
| Direct prices | 0.311 | 0.134 |

Every benchmark has a steeper slope within sectors than in the pooled sample,
and the ranking is unchanged: Moseley leads (0.61), Sraffa and Shaikh follow
(0.39 and 0.42), direct prices barely move (0.13). The fit is therefore not an
artefact of between-sector price levels.

## Measurement error

The value-added and gross-output deflators correlate at about 0.935 within
sector-year cells. Under a classical errors-in-variables assumption the
reliability of the value-added deflator as a proxy is about **0.61** (the
reverse-regression slope; `corr²` alone would suggest 0.87), so attenuation
could account for up to about 40% of the shortfall in the slopes. Even dividing
the reported slopes by that reliability leaves them well below one, and it does
not change the ranking.

## Gravitation on unit-price deviations

The unit-price deviation is:

```
d_it = log(price_obs_it / p_model_it)
```

Panel error-correction and one-year forecasts are in
`unit_price_gravitation.csv`. On unit prices **every** benchmark now carries a
negative output-adjustment coefficient, but only direct prices reach
significance (`β_GO = -0.058`, p=0.035). The Moseley variants sit between
`-0.10` and `-0.15` with p-values of 0.10-0.25; Sraffa and Shaikh at the plain
fixed point are essentially zero (`-0.02` and `-0.00`), while their
fixed-capital variants are negative and marginal (`-0.16`, p=0.095 and `-0.14`,
p=0.106). No benchmark beats the naive one-year forecast (log RMSE 0.065); the
Moseley variants are 0.14-0.18.

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

Pictures: `output/figures/findings_unit_prices.png` shows the scatter behind
this table, and `output/figures/findings_benchmark_fit.png` the revenue fit. Both
are explained in [`figures.md`](figures.md).
