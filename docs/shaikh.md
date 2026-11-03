# Moseley vs Shaikh: two classical benchmarks

This project implements two different answers to the same question: what is the
"center" around which market gross output gravitates?

## Moseley's benchmark

```
PP_i = K_i + R M_i
R = sum(S_i) / sum(M_i)
```

- `K_i = C_i + V_i` is the cost price.
- `M_i` is the **stock** of advanced capital: private fixed assets, government
  and housing capital, and inventories.
- `R` is the aggregate profit rate on the capital stock.
- Prices are gross annual industry revenues, not unit prices.

This is the macro-monetary, sequential interpretation: `S` and `R` are
determined at the aggregate level before prices of production.

## Shaikh's benchmark

Two Shaikh-style benchmarks are built from the BEA Use table.

**Direct prices / labour values**

```
lambda = l (I - A)^-1
```

`A` is the 2017 commodity-by-industry input matrix, and `l` is direct labour per
dollar of output. `lambda_i` is the total labour required per dollar of output
of industry `i`. Normalising `lambda_i * GO_i` to total gross output gives a
value-price benchmark `P_V`.

**Prices of production**

```
p = (1 + r)(p A + w l)
  = w (1 + r) l [I - (1 + r) A]^-1
```

`r` is a uniform profit rate on **flow capital**, set to the observed aggregate
`sum(S)/sum(K)`. The scale is fixed by normalising `p . GO` to total gross
output, giving `PP_S`.

The key difference from Moseley is the capital concept: Shaikh uses the flow
cost matrix and a uniform profit rate on cost; Moseley uses the stock of
advanced capital and `R = S/M`. The two are not nested.

## Iterative process

The direct solve is the Sraffian fixed point. The project also runs the
cost-plus iteration explicitly.

**Fixed-`r` iteration**

```
p_{k+1} = (1+r)(p_k A + w l)
```

with `r` fixed at the observed aggregate rate. It converges to the same ray as
the direct solve; it is a numerical check, not a different benchmark.

**Endogenous-`r` iteration**

```
c_k = p_k A + w l
r_k = (p_k y - c_k y) / (c_k y)
p_{k+1} = (1 + r_k) c_k
```

starting from labour values `p_0 = lambda`. This is the Shaikh-style cost-plus
process: the profit rate is recomputed from the price vector each round. On the
current data it converges in **27-28 rounds** (mean 26.7, all years converged)
with a residual below `1e-10`.

The model-implied rate averages **33.9%**, against an observed **30.3%**; for
2023 it is **35.7%** against **33.8%**. The iterated prices are very close to
the Sraffian fixed point: MAE **15.9%**, correlation **0.979**.

**Cross-dual simulation**

A minimal price/output adjustment is also simulated:

```
p_i' = p_i exp(-alpha (r_i - r_bar))
q_i' = q_i exp( beta  (r_i - r_bar))
```

Prices fall in high-profit industries (entry), output rises. Starting from
labour values, the weighted dispersion of profit rates falls from **0.142** to
approximately **zero** over about **194 steps**. This is a toy version of
turbulent gravitation, not a fully specified Shaikh model, but it does show the
adjustment mechanism converging toward equalised rates.

## Fit, 1998-2023, 65 market industries

| Benchmark | MAE | RMSE | corr | slope | within 25% | mean gap |
|---|---:|---:|---:|---:|---:|---:|
| Moseley `PP` | 13.7% | 22.9% | 0.983 | 1.043 | 88.8% | -7.2% |
| Shaikh `PP_S` | 15.9% | 20.1% | 0.977 | 0.954 | 80.7% | -1.0% |
| Shaikh iterated `PP_S_iter` | 15.9% | 20.1% | 0.979 | 0.954 | 80.5% | -1.1% |
| Shaikh `P_V` | 18.5% | 24.2% | 0.954 | 0.939 | 69.1% | -0.1% |

Reading:

- **Moseley wins on typical error and rank correlation.** It has the lowest MAE,
  the highest correlation, and the highest share of industries within ±25%.
- **Shaikh wins on aggregate calibration.** It has much lower mean bias (about
  -1% vs -7%), lower RMSE, and a slope closer to one.
- **Labour values alone fit worst.** Direct prices are a useful theoretical
  benchmark but not a good empirical price predictor.

## Gravitation, 1998-2023

| Benchmark | mean abs gap | half-life | GO beta | PP beta | 1y forecast RMSE |
|---|---:|---:|---:|---:|---:|
| Moseley `PP` | 12.4% | 2.2y | -0.163 (p=0.015) | +0.105 (p=0.035) | 0.213 |
| Shaikh `PP_S` | 16.8% | 3.2y | -0.216 (p=0.005) | -0.019 (p=0.742) | 0.255 |
| Shaikh iterated `PP_S_iter` | 16.8% | 3.4y | -0.204 (p=0.008) | -0.017 (p=0.778) | 0.255 |
| Shaikh `P_V` | 19.7% | 3.2y | -0.173 (p=0.003) | +0.020 (p=0.655) | 0.298 |

Naive forecast RMSE is 0.120.

Reading:

- **Moseley has smaller deviations and faster convergence.**
- **Shaikh has cleaner one-way gravitation.** Market output adjusts strongly
  toward `PP_S`, and `PP_S` does **not** adjust toward market output. That is
  closer to the theoretical notion of a center of gravitation.
- **Neither beats a random walk** at one year. Shaikh's forecast is worse than
  Moseley's, and both are worse than naive.

## Verdict

There is no single winner.

- If "fit" means typical industry-level accuracy and forecasting, **Moseley
  fits better**.
- If "fit" means aggregate calibration and a clean adjustment direction,
  **Shaikh fits better**.
- If "fit" means the labour theory of value directly, **both direct prices and
  Shaikh's flow-price benchmark do worse than Moseley's stock-based benchmark**.

The fixed point and the endogenous-r iteration are almost the same empirically:
MAE 15.9%, correlation 0.979. The iteration adds convergence diagnostics and a
model-implied profit rate, not a different price center. The cross-dual
simulation does equalise rates, but it is a toy process and is not used in the
fit comparison.

The most defensible summary: Moseley's benchmark is empirically closer to
observed gross output; Shaikh's benchmark is theoretically cleaner as a center
of gravitation but farther away and slower to converge. Neither predicts better
than a random walk.

## Caveats

- `A` is fixed at 2017, so the Shaikh prices are a 2017-technique benchmark with
  current labour inputs and profit rates.
- `A` excludes the non-produced `Used` and `Other` commodity rows (about 1.35%
  of intermediate use), to keep the matrix square.
- Industry labour hours are allocated in proportion to compensation.
- Shaikh's prices use a uniform profit rate on flow capital; Moseley's use the
  stock-based `R`. The comparison is between two different capital concepts,
  not two estimates of one parameter.
- Both benchmarks are gross revenue comparisons, not unit-price comparisons.
