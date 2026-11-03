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
current data it converges in **27 rounds on average** (maximum 34, all years
converged) with a residual below `1e-10`.

The model-implied rate averages **33.9%**, against an observed **30.3%**; for
2023 it is **35.7%** against **33.8%**. The iterated prices are very close to
the Sraffian fixed point: MAE **15.7%**, correlation **0.976**.

**Cross-dual simulation**

A minimal price/output adjustment is also simulated:

```
p_i' = p_i exp(-alpha (r_i - r_bar))
q_i' = q_i exp( beta  (r_i - r_bar))
```

Prices fall in high-profit industries (entry), output rises. Starting from
labour values, the weighted dispersion of profit rates falls from **0.146** to
approximately **zero** over about **199 steps**. This is a toy version of
turbulent gravitation, not a fully specified Shaikh model, but it does show the
adjustment mechanism converging toward equalised rates.

## Fit, 1998-2023, 65 market industries

| Benchmark | MAE | RMSE | corr | slope | within 25% | mean gap |
|---|---:|---:|---:|---:|---:|---:|
| Moseley `PP` | 13.7% | 22.9% | 0.983 | 1.043 | 88.8% | -7.2% |
| Shaikh `PP_S` | 15.7% | 19.5% | 0.975 | 0.974 | 81.2% | -1.6% |
| Shaikh iterated `PP_S_iter` | 15.7% | 19.6% | 0.976 | 0.975 | 82.0% | -1.7% |
| Shaikh `P_V` | 17.8% | 23.4% | 0.953 | 0.954 | 70.9% | -0.6% |

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
| Shaikh `PP_S` | 16.1% | 2.6y | +0.029 (p=0.235) | +0.264 (p<0.001) | 0.249 |
| Shaikh iterated `PP_S_iter` | 16.1% | 2.6y | +0.038 (p=0.101) | +0.274 (p<0.001) | 0.249 |
| Shaikh `P_V` | 18.7% | 2.7y | -0.043 (p=0.199) | +0.184 (p<0.001) | 0.293 |

Naive forecast RMSE is 0.120.

Reading:

- **Moseley has smaller deviations and faster convergence.**
- **Shaikh's earlier one-way gravitation was an artefact of the fixed 2017
  matrix.** With annual `A_t`, output does not adjust toward `PP_S`
  (`β = +0.029`, p=0.235), while `PP_S` adjusts strongly toward output
  (`β = +0.264`, p<0.001). The center moves toward the data, not the other way.
- **Neither beats a random walk** at one year. Shaikh's forecast is worse than
  Moseley's, and both are worse than naive.

## Verdict

There is no single winner.

- If "fit" means typical industry-level accuracy and forecasting, **Moseley
  fits better**.
- If "fit" means aggregate calibration, **Shaikh fits better**: lower RMSE,
  smaller mean bias, and a slope closer to one.
- If "fit" means the labour theory of value directly, **both direct prices and
  Shaikh's flow-price benchmark do worse than Moseley's stock-based benchmark**.

The fixed point and the endogenous-r iteration are almost the same empirically:
MAE 15.7%, correlation 0.976. The iteration adds convergence diagnostics and a
model-implied profit rate, not a different price center. The cross-dual
simulation does equalise rates, but it is a toy process and is not used in the
fit comparison.

The most defensible summary: Moseley's benchmark is empirically closer in
typical industry accuracy; Shaikh's is better calibrated in aggregate. Neither
is a clean center of gravitation once the input matrix is allowed to vary
annually, and neither predicts better than a random walk.

## Caveats

- `A` is annual and in current prices (1998-2023), so it mixes technical change
  with relative-price change. A constant-price `A_t` is the next step.
- `A` excludes the non-produced `Used` and `Other` commodity rows (about 1.35%
  of intermediate use), to keep the matrix square.
- Industry labour hours are allocated in proportion to compensation.
- Shaikh's prices use a uniform profit rate on flow capital; Moseley's use the
  stock-based `R`. The comparison is between two different capital concepts,
  not two estimates of one parameter.
- Both benchmarks are gross revenue comparisons, not unit-price comparisons.
