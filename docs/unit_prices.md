# Unit-price test

The revenue comparison asks whether `PP_i` tracks `GO_i`. Both are gross
revenues, so industry size can dominate. This test compares **relative unit
prices** instead.

## Construction

Observed price:

```
price_obs_i = BEA GDP-by-Industry gross-output price index / 100
```

Model prices:

```
p_moseley_i = PP_i / quantity_i
p_sraffa_i  = Sraffa price vector
p_shaikh_i  = Shaikh iterated price vector
p_reg_i     = p_sraffa_i * regulating_factor_i
p_v_i       = labour values
```

Every series is normalised per year to a quantity-weighted geometric mean of
one. The observed deflator is now the 71-industry BEA gross-output price index
(TableID 18), not a broad-sector GOPI series.

## Fit, 2005-2023

| Benchmark | log MAE | log RMSE | corr | slope | within 10% | within 25% |
|---|---:|---:|---:|---:|---:|---:|
| Moseley unit price (`PP/Q`) | 0.118 | 0.167 | 0.786 | 0.468 | 56.0% | 83.1% |
| **Moseley relative price (`PP/GO`)** | 0.160 | 0.224 | **0.050** | **0.047** | 43.7% | 75.6% |
| Moseley profit-rate relative price | 0.147 | 0.210 | 0.054 | 0.059 | 48.1% | 78.1% |
| Moseley working-capital relative price | 0.134 | 0.193 | 0.044 | 0.050 | 52.2% | 82.8% |
| Sraffa | 0.165 | 0.224 | 0.613 | 0.280 | 39.6% | 75.2% |
| Shaikh iterated | 0.168 | 0.216 | 0.652 | 0.305 | 34.5% | 75.3% |
| Regulating capital | 0.170 | 0.228 | 0.617 | 0.276 | 37.8% | 74.6% |
| Direct prices | 0.346 | 0.439 | 0.208 | 0.068 | 17.4% | 40.1% |

The earlier catastrophic result was largely a **coarse-deflator artifact**.
With 71-industry prices, Sraffa/Shaikh rise from about 0.1 to 0.61-0.65.

But the Moseley unit price is not a fair comparison. It is constructed as

```
p_moseley = PP / Q = (PP / GO) * price_obs
```

so it contains the observed price by construction. The fair model-relative-price
object is `PP/GO`, which has a correlation of only **0.05** with observed
relative prices. Moseley's 0.79 is therefore an anchoring artifact, not evidence
of superior relative-price content. On the fair comparison, Sraffa and Shaikh
have the only meaningful relative-price signal.

## Within-sector test

Because the observed price now varies within sectors, the within-sector test is
identified:

| Benchmark | corr within | slope within | RMSE within |
|---|---:|---:|---:|
| Moseley | 0.786 | 0.590 | 0.106 |
| Sraffa | 0.591 | 0.388 | 0.158 |
| Shaikh | 0.605 | 0.412 | 0.150 |
| Regulating | 0.588 | 0.380 | 0.161 |
| Direct prices | 0.315 | 0.132 | 0.292 |

The within-sector results are close to the full-sample results. That means the
fit is not driven by between-sector price levels; the model is picking up some
genuine within-sector relative-price variation, especially Moseley.

## Measurement error

The value-added and gross-output deflators are highly correlated within
sector-year cells (corr 0.935). Under a classical errors-in-variables
assumption, the reliability of the observed price is about `corr^2 ≈ 0.87`.
Correcting the slopes for that would give roughly:

- Moseley: 0.468 / 0.87 ≈ 0.54
- Sraffa: 0.295 / 0.87 ≈ 0.34
- Shaikh: 0.305 / 0.87 ≈ 0.35

Measurement error can explain some attenuation, but not the whole gap from one.
The corrected slopes remain well below one.

## Gravitation on unit-price deviations

| Benchmark | mean abs gap | half-life | GO beta | PP beta | 1y RMSE |
|---|---:|---:|---:|---:|---:|
| Moseley | 11.8% | 2.2y | -0.117 (p=0.160) | +0.158 (p=0.014) | 0.183 |
| Sraffa | 16.2% | 2.6y | -0.014 (p=0.548) | +0.218 (p<0.001) | 0.224 |
| Shaikh | 16.8% | 2.9y | -0.011 (p=0.657) | +0.202 (p<0.001) | 0.219 |
| Regulating | 16.7% | 2.6y | -0.014 (p=0.548) | +0.218 (p<0.001) | 0.228 |
| Direct prices | 34.6% | 3.3y | -0.050 (p=0.101) | +0.139 (p<0.001) | 0.450 |

Naive forecast RMSE is about 0.063. Every model is worse than a random walk.
For Sraffa/Shaikh/regulating prices, the model price adjusts toward the observed
price, not the reverse. Moseley is the only case with a negative output
coefficient, but it is not statistically significant.

## Revenue-ratio composition

`PP/GO` has mean 1.057, standard deviation 0.185, and a 5th-95th percentile
range of 0.83-1.37. Only 57.6% of observations are within ±10% and 86.1% within
±20%. The variance of `log(PP/GO)` is 0.0254, versus 0.0222 for observed log
prices. The revenue ratio accounts for **53%** of the variance of Moseley unit
prices — down from 79% with the broad-sector deflator, but still about half.

## Verdict

- The 71-industry prices materially improve the unit-price fit. The earlier
  result was substantially a measurement artifact.
- Moseley's revenue fit does **not** translate into relative prices. The
  `PP/Q` unit price looks good only because it is anchored to observed prices;
  the fair `PP/GO` series has corr 0.05 and slope 0.05.
- Sraffa/Shaikh/regulating prices reach corr 0.61-0.65 and within-sector corr
  0.59-0.61. They capture relative prices partially, not strongly, and are the
  only benchmarks with genuine relative-price content.
- Direct labour values remain poor (corr 0.21), so a simple labour-value price
  benchmark is not supported.
- Gravitation on unit prices is weak for all benchmarks, and forecasts are worse
  than a random walk.

The honest summary: **prices of production have real but partial unit-price
content; direct labour values do not.** The revenue fit overstates the unit-price
fit, but the unit-price fit is not zero once the deflator is measured at the
industry level.
