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
