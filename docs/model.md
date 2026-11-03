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

On the baseline sample the mean ratio is 1.011 and the mean gap is +56.8 bn
(+2.5% of `S`). Proprietors' income is mixed income, so the property measure is
an upper bound. The exercise is still informative because the gap is small and
stable.

## 8. Industry layer

The BEA summary Use table (producer prices, after redefinitions) gives 71
industries for 1997-2023. For industry `i`:

```
C_i    total intermediate consumption
V_i    compensation of employees
T_i    taxes on production and imports, less subsidies
GOS_i  gross operating surplus
N_i    total value added
GO_i   total industry output
```

The Marxian objects are:

```
S_i = T_i + GOS_i
K_i = C_i + V_i
r_i = S_i / K_i
R_cost = sum(S_i) / sum(K_i)
PP_K_i = K_i (1 + R_cost)
PP_V_i = V_i (1 + sum(S) / sum(V))
```

`R_cost` is a mark-up on **cost**, not the macro stock-based rate of profit.
`PP_K` assumes `M_i = K_i`; that is the main proxy limitation. `PP_V` is a
labour-only markup benchmark.

Because the Use table is an accounting identity, `C_i + N_i = GO_i` exactly.
A "value price vs. observed price" test at this level would therefore be
vacuous. The informative tests are:

- dispersion of `r_i` (weighted CV, p90/p10);
- mean absolute percentage error of `PP_K` and `PP_V` against `GO_i`;
- correlation and log-log slope of `GO_i` on each benchmark.

Housing (`HS`) is mostly imputed rent with almost no measured intermediate
cost, and government units are not capitalist enterprises. They remain in the
full sample but are excluded from a market-industry robustness subset, because
otherwise the dispersion statistic is dominated by one structural outlier.
