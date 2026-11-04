# Unit-price test

The revenue comparison asks whether `PP_i` tracks `GO_i`. Both are gross
revenues, so industry size can dominate. This test compares **relative unit
prices** instead.

## Construction

Observed price:

```
price_obs_i = GOPI_i / 100
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
one, so the comparison is about relative prices. Levels are arbitrary.

## Fit, 2005-2023

| Benchmark | log MAE | log RMSE | corr | slope | within 10% | within 25% |
|---|---:|---:|---:|---:|---:|---:|
| Moseley `PP` | 0.122 | 0.172 | 0.504 | 0.212 | 54.6% | 82.6% |
| Sraffa | 0.170 | 0.225 | 0.109 | 0.037 | 37.1% | 74.3% |
| Shaikh iterated | 0.171 | 0.219 | 0.180 | 0.063 | 32.8% | 76.0% |
| Regulating capital | 0.173 | 0.228 | 0.127 | 0.042 | 35.6% | 72.2% |
| Direct prices | 0.359 | 0.455 | -0.086 | -0.012 | 16.3% | 38.4% |

The revenue fit weakens sharply at the unit-price level. Moseley is clearly best
(corr 0.50, MAE 0.12), but its slope is still only 0.21. Sraffa, Shaikh and
regulating prices have correlations of 0.11-0.18 and slopes near 0.05. Direct
prices are worst.

## Gravitation on unit-price deviations

| Benchmark | mean abs gap | half-life | GO beta | PP beta | 1y RMSE |
|---|---:|---:|---:|---:|---:|
| Moseley | 12.2% | 1.7y | -0.179 (p=0.002) | +0.150 (p=0.013) | 0.178 |
| Sraffa | 17.0% | 2.6y | -0.003 (p=0.883) | +0.228 (p<0.001) | 0.224 |
| Shaikh | 17.1% | 2.8y | +0.0003 (p=0.987) | +0.219 (p<0.001) | 0.219 |
| Regulating | 17.3% | 2.6y | -0.003 (p=0.883) | +0.228 (p<0.001) | 0.228 |
| Direct prices | 35.9% | 3.4y | -0.029 (p=0.199) | +0.157 (p<0.001) | 0.452 |

Naive forecast RMSE is about 0.052. Every model is worse than a random walk.

Moseley's unit prices show two-way adjustment. Sraffa/Shaikh/regulating prices
show no output adjustment: the model price moves toward the observed price, not
the reverse.

## The main caveat

The observed price is a **broad-sector gross-output deflator**. There are only
about 18 distinct values across 65 industries, with a cross-sectional standard
deviation of about 0.08. The model prices vary much more (standard deviation
about 0.22). A low correlation is therefore partly a data-resolution problem:
the test cannot see within-sector relative prices.

This does not rescue the model. It means the unit-price test is currently a
coarse test. The next improvement is industry-level or commodity-level price
indexes, not more model structure.

## Verdict

- The strong revenue fit is largely a size effect. Once prices are compared
  directly, all benchmarks are weak.
- Moseley remains the best unit-price benchmark, but with a slope of 0.21 and
  correlation 0.50.
- Sraffa/Shaikh/regulating prices are better calibrated in aggregate revenue but
  do not match relative prices at all.
- Labour values are the worst by a wide margin.

The honest summary: **the empirical case for the LTV is much weaker at the
unit-price level than at the revenue level.** This is exactly why the unit-price
test was worth running.
