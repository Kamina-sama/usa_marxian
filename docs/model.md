# The model, transcribed and mapped to data

Source: Fred Moseley, *Money and Totality* (Brill, 2016), chapter 2,
"The Algebraic Summary", pp. 27-40. Equation numbers below are Moseley's.

## 1. Production of surplus-value

The circuit of money capital, applied to total social capital:

```
M - C ... P ... C' - M'          M' = M + ΔM
```

`M` is the money capital advanced at the beginning of the year; it is the
initial given of the theory, not a derived magnitude.

### Cost price

```
(1)  S = P - K
(2)  K = C + V
(2') K = C̄ + V̄
```

`C` is consumed constant capital: depreciation of fixed capital plus
circulating constant capital used up in the year. `V` is variable capital, the
annual wage bill. Bars indicate magnitudes taken as given because they were
advanced in circulation before production.

### Value-price

```
(3)  P = C̄ + N
(4)  N = m L
(5)  P = C̄ + m L
```

`P` is the value-price (money form of value) of the year's output. `N` is new
value, produced by current labour. `L` is socially necessary labour time in
hours, and `m` is the money new value produced per hour — Foley's "monetary
expression of labour time" (MELT).

Substituting (2') and (3) into (1):

```
(6)  S = (C̄ + N) - (C̄ + V̄)
```

Constant capital appears in both the value-price and the cost price, so it
cancels:

```
(7)  S = N - V̄ = m L - V̄
```

This is Marx's "dual significance of constant capital". Two consequences:

- constant capital is a determinant of the value-price but **not** of
  surplus-value;
- the empirical measure of `S` is invariant to whether `C` is measured
  narrowly (depreciation) or broadly (intermediate inputs plus depreciation).

### Average worker

```
(8)  S_i = m L_i - V̄_i = m (L_i - NL_i) = m SL_i
(9)  S   = (d n) (m SL_i)
```

`NL_i = V_i / m` is necessary labour, `SL_i = L_i - NL_i` is surplus labour,
`n` is the number of workers and `d` the number of working days per year.

## 2. Distribution of surplus-value

```
(10) PP_i = K̄_i + R M̄_i
(11) R    = S / M̄
```

`PP_i` is the price of production of industry `i`, understood as **gross annual
industry revenue**, not a unit price. `M̄_i` is the total stock of capital
invested in the industry. The general rate of profit is determined *before*
prices of production and then presupposed by them.

Industry-level value prices:

```
(12) P_i = C̄_i + N_i
(13) N_i = V̄_i + S_i
(14) P_i = C̄_i + V̄_i + S_i
(15) P_i = K̄_i + S_i
```

Comparing (10) and (15): the cost-price component is identical in the value
system and the price system. Only the second component differs — surplus-value
versus average profit. The inputs therefore do not need to be "transformed";
they remain invariant. This is the core of Moseley's dissolution of the
transformation problem.

## 3. The two aggregate equalities

Because `R = S/M`:

```
Σ π_i = Σ R M_i = R Σ M_i = R M = (S/M) M = S
```

And because the same `C` and `V` are used at both levels:

```
Σ PP_i = Σ (K_i + R M_i) = K + R M = K + S = P
```

Both equalities hold simultaneously in the general case, not only when
compositions of capital are equal.

## 4. Empirical implementation

### Net value-added layer (default)

| Moseley | Meaning | US series | Notes |
|---|---|---|---|
| `P` | total value-price | `GDPA` | GDP, current prices |
| `C` | consumed constant capital | `COFC` | consumption of fixed capital |
| `N` | new value | `GDPA - COFC` | net domestic product |
| `V` | variable capital | `A033RC1A027NBEA` | compensation of employees |
| `S` | surplus-value | `N - V` | net operating surplus + taxes on production |
| `K` | cost price | `C + V` | |
| `M` | advanced capital | `K1NTOTL1ES000` + inventories | net fixed assets + inventory stock |
| `L` | labour hours | `HOANBS x NIPA 2017 benchmark` | see hours methods |
| `m` | MELT | `N / L` | USD of new value per hour |
| `R` | general rate of profit | `S / M` | |

The identities hold numerically:

```
P = C + N        (because N := P - C)
S = N - V
S = P - K
R = (S/V) / (M/V)
```

`K100071A027NBEA` is an opening balance: the value for year `t` is the stock at
the start of `t`. The code shifts it forward one year so that `M` uses an
end-of-year inventory stock, consistent with the fixed-asset stock.

### Hours methods

- `indexed` (default): nonfarm business hours index (`HOANBS`) scaled to the
  NIPA 2017 benchmark. Long history (1947-present) and current, but assumes the
  nonfarm business composition is stable.
- `nipa`: NIPA table 6.9 hours worked, total economy. Better coverage, but the
  series currently ends in 2022.
- `ces`: total private employment times average weekly hours times 52. Current
  and consistent, but excludes government and self-employed workers, and the
  FRED weekly-hours series only starts in 2006.

### What the MELT is not

`m = N/L` is recovered residually. Its level is therefore an accounting
artefact of the chosen `N` and `L`; only its *dynamics* and its relation to
other variables carry information. Moseley's own empirical work uses variants
(NNP, NDP, net national income) and discusses the choice explicitly.

### Known measurement issues

- **Mixed income.** Compensation of employees excludes proprietors' income,
  which contains both labour and property income. `S = N - V` therefore
  overstates surplus-value relative to a fully imputed labour share.
- **Depreciation.** `COFC` is accounting depreciation, not Marx's moral
  depreciation or the value transferred by fixed capital in a labour-time
  sense.
- **Capital stock.** Net fixed assets at current cost is a proxy for `M`. It
  excludes inventories unless they are added, and it is a net rather than gross
  stock.
- **Taxes.** `S` includes taxes on production and imports, which are part of
  surplus-value distributed to the state, not profit appropriated by capital.
  For a profit-only comparison, use `net_operating_surplus` plus corporate
  profits as an independent check.
- **Prices of production.** `PP_i` are gross annual revenues. Comparing them
  with unit prices or with value prices requires IO tables and a consistent
  treatment of fixed capital.

## 5. Differences from the standard interpretation

Moseley's reading is a **single-system**, **sequential**, **macro-monetary**
interpretation:

- one system (actual capitalism), not a hypothetical value system followed by
  a price system;
- the total surplus-value is determined first, at the aggregate level; the
  rate of profit is `S/M` and is prior to prices of production;
- inputs are actual money capital magnitudes and remain invariant in the
  transition to prices of production;
- the MELT is not affected by the transformation of values into prices.

The standard (Bortkiewicz-Sweezy/Sraffian) reading starts from physical
quantities, derives values, and then transforms them. The empirical difference
is that the standard reading needs an IO matrix and simultaneous price
determination, while Moseley's reading needs only the aggregate money accounts
for the distribution results.

## 6. Robustness specifications

`build_accounts` exposes four switches. The robustness module varies one at a
time:

- `value_added`: `ndp` (default), `nnp` (`GNP - CFC`), or `nnp_factor`
  (net national factor income).
- `capital_stock`: `nonresidential` (default) or `private_total`.
- `include_inventories`: whether inventory stock enters `M`.
- `melt_numerator`: `ndp`, `nnp`, `nnp_factor`, or `gdp`.

The identities hold under every combination; only the measured magnitudes
change. This matters most for the profit-rate denominator: private total fixed
assets are roughly twice nonresidential assets, so the last-year profit rate
ranges from about 12.9% to 26.6% across specifications. The LTV slope is much
more stable, at 1.54-2.25.

`nnp_factor` is a factor-cost measure: it excludes taxes on production. That is
why its property-income ratio is about 1.32 rather than 1.01. It is a
legitimate alternative new-value concept, not an error.

## 7. Property-income check

`S = N - V` is an accounting residual, so a "profit = surplus-value" test needs
an independent profit measure. NIPA property income provides one:

```
property_income = corporate_profits + proprietors_income
                  + net_interest + rental_income
```

Adding taxes on production gives a total that should approximate `S`:

```
property_income + taxes_on_production  ~  S
```

On the baseline sample the mean ratio is 1.011 and the mean gap is +58.2 bn
(+2.5% of `S`). Proprietors' income is mixed income, so the property measure is
an upper bound. The exercise is still informative because the gap is small and
stable.

## 8. Industry layer

The BEA summary Use table (producer prices, after redefinitions) gives 71
industries for 1997-2023; the net CFC-adjusted sample starts in 1998. For
industry `i`:

```
C_i    total intermediate consumption
V_i    compensation of employees
T_i    taxes on production and imports, less subsidies
GOS_i  gross operating surplus
N_i    total value added
GO_i   total industry output
```

Gross and net Marxian objects are:

```
S_gross_i = T_i + GOS_i
K_gross_i = C_i + V_i

S_net_i = T_i + GOS_i - CFC_i
K_net_i = C_i + CFC_i + V_i
N_net_i = N_i - CFC_i
```

Both satisfy `K_i + S_i = GO_i`. The Use table's GOS is gross of depreciation,
so the gross split leaves CFC in surplus-value. The net split is the correct
Marxian treatment.

CFC is parsed from BEA NIPA tables 6.13D and 6.22D, allocated within broad
sectors in proportion to GOS, and the residual between total-economy `COFC` and
private CFC is allocated to government units. On the current vintage the
industry CFC total equals macro `COFC` exactly.

Prices of production follow the general formula:

```
PP_i = K_i + R M_i,        R = sum(S_i) / sum(M_i)
PP_V_i = V_i (1 + sum(S) / sum(V))
```

`M_i` is the actual BEA fixed-asset stock plus private inventory stock. Private
nonresidential fixed assets come from the 74 detailed industries, mapped to 65
IO industries. Government/housing capital comes from Fixed Assets Sections 7
and 5: federal defense/nondefense, state/local general government, state/local
government enterprises, and owner-occupied residential stock. Manufacturing and
retail inventories come from BEA Table 1BUC at detailed NAICS level; farm,
mining/utilities/construction, wholesale and “other” come from Table 5.8.5B and
are allocated within the broad group.

Older proxies remain available for sensitivity: `cost` (`M_i = K_i`), `output`
(`M_i = GO_i`), and `value_added` (`M_i = N_i`). The old `K_i(1+R)` expression is
only the cost-proxy special case. `PP_V` is a labour-only markup benchmark.

Because the Use table is an accounting identity, `C_i + N_i = GO_i` exactly.
A "value price vs. observed price" test at this level would therefore be
vacuous. The informative tests are:

- dispersion of `r_i` (weighted CV, p90/p10);
- mean absolute percentage error of `PP` and `PP_V` against `GO_i`;
- correlation and log-log slope of `GO_i` on each benchmark;
- sensitivity of the fit to the `M_i` proxy.

Housing (`HS`) is mostly imputed rent with almost no measured intermediate
cost, and government units are not capitalist enterprises. They remain in the
full sample but are excluded from a market-industry robustness subset, because
otherwise the dispersion statistic is dominated by structural outliers.

Sector deflation uses broad-sector chain-type price indexes from the BEA
GDP-by-Industry release (`VAPI*` for value added, `GOPI*` for gross output).
Intermediate consumption uses a supplier-weighted input deflator: 2017 Use-table
weights applied to the broad-sector gross-output deflators of the supplying
commodities. Real intermediate consumption is not constructed as
`GO_real - N_real`; the direct deflator avoids that invalid residual.

## 9. Accounting audit

The audit checks five places where costs could be counted twice:

1. **Macro `P = C + N`.** `P = GDP`, `C = CFC`, `N = NDP`. Since
   `GDP = CFC + NDP`, the identity is exact. `K = C + V` and `S = N - V`.
   Depreciation is in both `P` and `K`, so it cancels from `S`.
2. **`M` is a stock, not a flow.** `M` is net fixed assets plus inventories.
   `C` is the annual CFC flow. They are different objects and are not summed
   into the same total.
3. **Industry `K_gross = C + V`.** `C` is intermediate consumption; `V` is
   compensation. Neither contains the other. `T`, `GOS` and `N` are separate
   value-added components.
4. **Industry `K_net = C + CFC + V`.** CFC is added once. `S_net` subtracts
   the same CFC once. `K_net + S_net = GO` still holds.
5. **Cross-industry sums.** Summing `GO_i` or `K_i` double counts intermediate
   deliveries. Only `sum(N_i)` is a value-added aggregate. The code uses
   `sum(N_i)` only for reconciliation, never as GDP.

Reconciliation for 2023:

- industry CFC minus macro `COFC`: 0.0 bn;
- industry value added minus GDP: -105.2 bn (0.38%, BEA IO/GDP discrepancy);
- industry net value added minus NDP: the same -105.2 bn;
- industry net surplus-value minus macro `S`: -80.3 bn (0.9%).

What is still approximate: the within-sector CFC allocation, the broad
inventory allocation for mining/utilities/construction and “other” industries,
and the broad-sector commodity price proxies in the intermediate-input
deflator.

## 10. Predictive and gravitation tests

If prices of production are centers of gravitation, the deviation

```
d_it = log(GO_it / PP_it)
```

should be temporary, and market gross output should adjust toward `PP` when
`d` is non-zero. The project tests this with panel error correction:

```
Δ log GO_it = α_i + γ_t + β_GO d_i,t-1 + ε_it
Δ log PP_it = α_i + γ_t + β_PP d_i,t-1 + ε_it
```

and with expanding-window out-of-sample forecasts of `GO` at 1, 3 and 5 years.
The results are in `docs/gravitation.md`. With actual capital stocks the gap
closes through both channels: `β_GO = -0.163` (p=0.015) and `β_PP = +0.105`
(p=0.035). A slow-moving long-run centre is also tested:

```
PP*_it = K_trend_it + R_long_t * M_trend_it
```

using five-year trailing averages. It shows stronger mean reversion
(`β_GO = -0.134`, p=0.001) and a 1.8-year half-life. Neither benchmark beats a
naive random-walk forecast, so the evidence is best described as slow gravitation
without predictive power.

## 11. Sraffa's prices of production and Shaikh's process

For comparison, the project builds Sraffian prices of production and classical
labour values from **deflated** annual BEA Use matrices (2005-2023, 2017 dollars):

```
A_t,ij = U_t,ij / GO_t,j          (deflated to 2017 dollars)
l_t,j  = L_t,j / GO_real_t,j
lambda_t = l_t (I - A_t)^-1
p_t = (1 + r_t)(p_t A_t + w l_t)
```

`r` is the real aggregate surplus-value rate on flow capital,
`sum(S_real)/sum(K_real)`. Relative prices are independent of `w`; the scale is
fixed by normalising to total real output, and the resulting benchmarks are
reflated to nominal for comparison with observed gross output.

The comparison is on 65 market industries, 2005-2023:

- Moseley: MAE 13.7%, RMSE 23.0%, corr 0.983, slope 1.046, mean gap -7.4%.
- Sraffa: MAE 16.8%, RMSE 20.5%, corr 0.971, slope 0.982, mean gap -2.4%.
- Shaikh iterated: MAE 17.2%, RMSE 21.3%, corr 0.973, mean gap -3.1%.
- Direct labour values: MAE 18.6%, RMSE 23.6%, corr 0.954, mean gap -1.3%.

Moseley fits typical industry errors better; Sraffa has lower aggregate bias, a
slope closer to one, and lower RMSE. With constant-price `A_t`, Sraffa's clean
one-way gravitation still disappears: `β_GO = +0.068` (p=0.195) and
`β_PP = +0.341` (p<0.001). The center adjusts toward the data, not the other
way. Neither beats a naive forecast.

The direct solve is the Sraffian fixed point. The project also runs the explicit
Shaikh cost-plus iteration:

```
p_{k+1} = (1 + r_k)(p_k A + w l)
r_k = (p_k y - (p_k A + w l)y) / ((p_k A + w l)y)
```

starting from labour values. It converges in 29 rounds on average (maximum 34),
with a model-implied real profit rate averaging 35.9% against an observed 23.2%.
The iterated prices are almost identical to the fixed point (MAE 17.2%, corr
0.973). A toy cross-dual price/output simulation reduces profit-rate dispersion
from 0.160 to approximately zero. See `docs/sraffa.md` and `docs/shaikh.md`.
