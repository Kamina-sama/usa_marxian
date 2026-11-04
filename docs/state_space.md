# State space for Shaikh-style real competition

This dataset is the measurement layer for a stock-flow cross-dual model. It is
not yet the behavioural model. It contains one row per market industry-year and
a long annual input-output matrix.

## Coverage

- 65 market industries; government units and housing are excluded
- 2005-2023 complete state data (19 years, 1,235 observations)
- 26 current-price annual matrices, 1998-2023
- 19 deflated real matrices, 2005-2023
- 86,518 non-zero current-price matrix entries; 63,261 real entries

Complete state data start in 2005 because the broad-sector GDP-by-Industry price
indexes start then. The annual matrices themselves cover 1998-2023.

## Variables

| Variable | Definition | Source |
|---|---|---|
| `price` | gross-output price index, 2017 = 1 | BEA GDP-by-Industry TableID 18 (71 industries) |
| `quantity` | real gross output, millions of 2017 dollars | `GO / price` |
| `capital` | real net fixed capital stock, millions of 2017 dollars | BEA `detailnonres_stk2` |
| `investment` | real gross investment, millions of 2017 dollars | BEA `detailnonres_inv1` deflated by the implicit capital deflator |
| `depreciation` | real depreciation, millions of 2017 dollars | BEA `detailnonres_dep1` deflated similarly |
| `utilization` | output-capital ratio, normalised to 1 in 2017 | `quantity / capital` |
| `wage_rate` | aggregate money wage, dollars per hour | macro `V / L` |
| `wage_rate_i` | industry money wage, dollars per hour | `V_i / labour_hours_i` |
| `fte` | full-time equivalent employees, thousands | BEA Table 6.5D |
| `labour_hours` | industry labour hours | `fte * 1000 * hours_per_fte` |
| `labour_coefficient` | hours per current dollar of output | `labour_hours / (GO * 1e6)` |
| `labour_coefficient_real` | hours per 2017 dollar of output | `labour_hours / (quantity * 1e6)` |
| `capital_current` | current-cost net fixed capital stock, millions | BEA `detailnonres_stk1` |
| `capital_real` | fixed-cost net stock, millions of 2017 dollars | BEA `detailnonres_stk2` |

The matrix file has columns `year`, `commodity_code`, `industry_code`, `value`,
where `value = U_t[c, j] / GO_t[j]`.

## Construction

```
price_i      = GOPI_sector(i) / 100
quantity_i   = GO_i / price_i
capital_i    = M_real_i
deflator_i   = M_current_i / M_real_i
investment_i = I_current_i / deflator_i
depreciation_i = D_current_i / deflator_i
utilisation_i = (quantity_i / capital_i) / mean_2017(quantity_i / capital_i)
wage_rate_t  = V_t / L_t
labour_i     = V_i / wage_rate_t
```

The capital deflator is the implicit deflator from the current-cost and
fixed-cost stock files. `A_t` is the annual current-price Use matrix.

## What is still approximate

- **Prices and quantities** are based on broad-sector gross-output deflators,
  not industry-level or commodity-level price indexes.
- **`A_t` is in current prices.** It mixes technical change with relative-price
  change. A constant-price `A_t` is the next refinement.
- **Utilization** is an output-capital ratio, not the FRB capacity-utilization
  series. FRB utilization is available only for manufacturing aggregates.
- **Labour hours** are built from Table 6.5D full-time equivalents. Manufacturing
  hours-per-FTE is calibrated to BLS CES manufacturing totals; other industries
  use the aggregate hours-per-FTE. True industry-specific hours would require
  BLS CES detail, which is not available for all 71 industries.
- **Wages** now include an industry wage rate `wage_rate_i = V_i / hours_i`, but
  the aggregate wage is still used for the macro wage rule.
- **Depreciation** is BEA fixed-asset depreciation, not the NIPA CFC allocation
  used in the industry accounts.

## How to use it

The state vector for a cross-dual model is:

```
p_i, q_i, k_i, I_i, u_i, w, l_i, A_t
```

A minimal stock-flow system can then be written as:

```
p_i = (1 + m_i)(p A_i + w l_i)
\dot m_i = α (r_i - r̄)
\dot q_i/q_i = β (D_i - q_i)/q_i
I_i/k_i = γ0 + γ1 (r_i - r̄) + γ2 (u_i - ū)
\dot k_i = I_i - δ_i k_i
\dot w/w = φ(employment, productivity, inflation)
```

with demand `D_i` closing the system. The current dataset supplies every
variable on the right-hand side except demand and the behavioural parameters.

## Files

- `data/processed/state_space.csv` — industry-year state table
- `data/processed/technical_matrices.csv` — long annual current-price `A_t`
- `data/processed/technical_matrices_real.csv` — deflated annual `A_t` used by the stock-flow model
- `data/processed/state_space_macro.csv` — macro wage, hours and aggregates
- `data/processed/state_space.json` — coverage summary
