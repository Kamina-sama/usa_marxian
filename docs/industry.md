# Industry layer: data, construction and caveats

## Source

BEA input-output archive (keyless):

```
https://apps.bea.gov/industry/iTables%20Static%20Files/AllTablesIO.zip
```

The project parses
`IOUse_After_Redefinitions_PRO_1997-2023_Summary.xlsx`: annual sheets, 71
summary industries, producer prices, after redefinitions.

Additional sources:

- BEA NIPA Section 6 workbook (keyless):
  `https://apps.bea.gov/national/Release/XLS/Survey/Section6All_xls.xlsx`
  Tables 6.13D and 6.22D give noncorporate and corporate capital consumption
  allowances by industry.
- BEA fixed-asset detail (keyless):
  `https://apps.bea.gov/national/FA2004/Details/xls/detailnonres_stk1.xlsx`
  Current-cost net stock of private nonresidential fixed assets by detailed
  industry, 1925-present.
- BEA NIPA Section 5 workbook (keyless):
  `https://apps.bea.gov/national/Release/XLS/Survey/Section5All_xls.xlsx`
  Table 5.8.5B gives private inventory stocks by broad industry.
- FRED broad-sector chain-type price indexes from the GDP-by-Industry release:
  `VAPI*` for value added and `GOPI*` for gross output, 2017=100.

## Extracted fields

| Field | Meaning |
|---|---|
| `C` | total intermediate consumption |
| `V` | compensation of employees |
| `T` | taxes on production and imports, less subsidies |
| `GOS` | gross operating surplus (gross of CFC) |
| `N` | total value added (gross) |
| `GO` | total industry output |

## Gross and net accounts

```
S_gross_i = T_i + GOS_i
K_gross_i = C_i + V_i

S_net_i = T_i + GOS_i - CFC_i
K_net_i = C_i + CFC_i + V_i
N_net_i = N_i - CFC_i
```

Both satisfy `K_i + S_i = GO_i`. The gross split is what the Use table alone
supports. The net split is the correct Marxian treatment because GOS includes
depreciation.

CFC allocation:

1. Parse corporate and noncorporate CFC by broad sector.
2. Allocate within each sector to IO industries in proportion to GOS.
3. Allocate the residual between total-economy CFC (`COFC`) and private CFC to
   government units in proportion to their value added.

The allocation is explicit and does not double count: `C_i` is intermediate
consumption, `CFC_i` is depreciation, and `K_net_i` adds both once.

Reconciliation on the current vintage:

- industry CFC = macro `COFC` exactly (4,576.4 bn in 2023);
- industry value added minus GDP = -105.2 bn (BEA IO/GDP statistical
  discrepancy, 0.38%);
- industry net value added minus NDP = the same -105.2 bn;
- industry net surplus-value minus macro `S` = -80.3 bn (0.9%).

## Prices of production

Moseley's general formula is:

```
PP_i = K_i + R M_i,        R = sum(S_i) / sum(M_i)
```

`M_i` combines two BEA sources:

- current-cost net stock of private nonresidential **fixed assets**, mapped from
  74 detailed industries to 65 of the 71 IO industries;
- year-end private **inventory stocks** from NIPA Table 5.8.5B, allocated from
  broad sectors to IO industries in proportion to gross output.

Government units and housing have no private nonresidential stock and fall back
to `K_i`, flagged as `cost_proxy`.

Coverage in 2023: 65 of 71 industries actual. Fixed assets 34,948 bn vs macro
34,771 bn (+0.51%); inventories 3,805 bn vs macro 3,805 bn (0.0%); combined
38,753 bn vs 38,576 bn (+0.46%). The inventory totals are official; the
within-sector allocation is a proxy.

Older proxies remain available for sensitivity:

| Proxy | `M_i` | Meaning |
|---|---|---|
| `fixed_assets+inventories` | BEA fixed assets + allocated inventories | default |
| `cost` | `K_i` | the old `K_i(1+R)` special case |
| `output` | `GO_i` | capital proportional to gross output |
| `value_added` | `N_i` | capital proportional to value added |

`sum(PP_i) = sum(GO_i)` holds for every proxy because `R` is defined from the
same aggregate `M`. The informative comparison is the distance between `PP_i`
and observed gross output, not the aggregate identity.

## Sector deflation

Value added, compensation and gross output are deflated with broad-sector
chain-type price indexes:

```
N_real_i = N_net_i / (VAPI_sector / 100)
V_real_i = V_i / (VAPI_sector / 100)
GO_real_i = GO_i / (GOPI_sector / 100)
S_real_i = N_real_i - V_real_i
```

Real intermediate consumption is **not** constructed as `GO_real - N_real`:
with different deflators that residual is not a valid volume and can be
negative. A real profit rate would require a sector intermediate-input
deflator, which the summary Use table does not provide.

## Structural outliers

`HS` (Housing) is mostly imputed rent with almost no measured intermediate
cost. `GFGD`, `GFGN`, `GFE`, `GSLG` and `GSLE` are government units, not
capitalist enterprises. Both are kept in the full sample but excluded from the
market-industry subset, which is the headline sample.

## Results, 1998-2023, net basis

- Market general rate of profit `R = S/M`: 20.2% in 2023; full sample 20.7%.
- Market surplus-value rate on cost `S/K`: 23.8%.
- Market weighted CV of `r_i`: 0.609 in 2023 (sample mean 0.703); p90/p10 6.10.
- Full-sample CV: 2.109 in 2023 (sample mean 2.296), dominated by housing and
  government.
- MAE of `PP` vs gross output: 16.3% full, 13.5% market-only.
- MAE of `PP_V` vs gross output: 53.1%.
- Correlation of `PP` with gross output: 0.888 full, 0.983 market-only.
- Share within 25% of `PP`: 83.7% full, 89.5% market-only.
- Proxy sensitivity, full-sample MAE: fixed assets + inventories 16.3%, cost
  13.3%, output 11.0%, value-added 9.0%. Market-only MAE: 13.5%, 10.5%, 8.7%,
  7.1%.
- Sector-deflated real growth, 2005-2023: value added 1.80%/yr, gross output
  1.67%/yr.

Interpretation: actual capital stocks fit **worse on average error** than the
cost proxy, though the market cross-sectional correlation is high (0.983). That
is informative: with `M_i = K_i`, `PP_i` is mechanically close to `GO_i`, so the
old fit was partly built in. Actual capital stocks expose the profit-rate
dispersion, especially regulated utilities and capital-intensive industries.
The equalised-profit benchmark still tracks gross output much better than a
labour-only markup, but industry surplus-value rates are far from equalised.
The result is consistent with competition plus persistent industry-specific
rents and adjustment costs. It is not a decisive test of the transformation
procedure.

## Predictive tests

The industry panel is also used to test whether prices of production are
centers of gravitation for market gross output. That analysis has its own
document: `docs/gravitation.md`.

Short version: on the 65 market industries, deviations have a mean absolute
value of 12.8% and a half-life of about 2.2 years. The error-correction evidence
supports slow, two-way gravitation: market output adjusts toward PP (β=-0.157,
p=0.018) and PP also adjusts toward market output (β=+0.110, p=0.019). PP still
does not beat a random walk in out-of-sample forecasts.

## Next steps

- Replace the gross-output allocation of broad-sector inventories with
  industry-level inventory data.
- Build a sector intermediate-input deflator for real cost prices and profit
  rates.
- Use Make and Use tables to compute labour values via the Leontief inverse.
- Build unit prices by dividing gross output by quantity indices.
