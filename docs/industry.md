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
- BEA Fixed Assets Sections 7 and 5 (keyless):
  `https://apps.bea.gov/national/FixedAssets/Release/XLS/Section7All_xls.xlsx`
  and `Section5All_xls.xlsx` for government and owner-occupied residential
  capital stocks.
- BEA NIPA Section 5 workbook (keyless):
  `https://apps.bea.gov/national/Release/XLS/Survey/Section5All_xls.xlsx`
  Table 5.8.5B gives private inventory stocks by broad industry.
- BEA NIPA underlying detail (keyless iTable core API):
  `https://apps.bea.gov/iTable/core/data/app/GetStep`
  Table 1BUC gives detailed manufacturing and retail inventories.
- BEA GDP-by-Industry tables (requires a free `BEA_API_KEY`) for the
  71-industry value-added, gross-output, intermediate-inputs and quantity
  indexes. The keyless fallback is the FRED broad-sector chain-type price
  indexes from the same release: `VAPI*` for value added and `GOPI*` for gross
  output, 2017=100.

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

`M_i` combines three BEA sources:

- current-cost net stock of private nonresidential **fixed assets**, mapped from
  74 detailed industries to 65 IO industries;
- **government and housing capital** from BEA Fixed Assets Sections 7 and 5:
  federal defense/nondefense, state/local general government, state/local
  government enterprises, and owner-occupied residential stock;
- year-end private **inventory stocks**: manufacturing and retail from BEA
  Table 1BUC at detailed NAICS level (23 IO industries, 53.7% of inventory
  value); farm, mining/utilities/construction, wholesale and “other” from NIPA
  Table 5.8.5B, allocated within the broad group by gross output.

Coverage in 2023: **all 71 industries use actual capital**, with no cost proxy.
Private nonresidential fixed assets are 34,948 bn vs macro 34,771 bn (+0.51%);
government and housing add 47,797 bn; inventories are 3,805 bn and match the
macro stock. Total capital assets are 82,746 bn. The market sample excludes
government and housing and is the headline comparison.

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

Value added, compensation and gross output are deflated with the BEA
GDP-by-Industry 71-industry chain-type price indexes:

```
N_real_i = N_net_i / (VAPI_i / 100)
V_real_i = V_i / (VAPI_i / 100)
GO_real_i = GO_i / (GOPI_i / 100)
S_real_i = N_real_i - V_real_i
```

Intermediate consumption uses the separate intermediate-inputs index
(TableID 23; `INPI` in the BEA release):

```
C_real_i = C_i / (INPI_i / 100)
K_real_i = C_real_i + V_real_i
r_real_i = S_real_i / K_real_i
R_real_i = S_real_i / M_real_i
```

All three are industry-level indexes, so no supplier weighting is required.
Capital is deflated by the industry's own gross-output index.

Without a `BEA_API_KEY` the project falls back to broad-sector FRED `VAPI*` /
`GOPI*` indexes, and `C_i` is then deflated by a supplier-weighted proxy built
from 2017 Use-table input shares and the supplying sectors' gross-output
deflators.

On 2023 the real market profit rate is 20.2% vs 20.2% nominal, and real
dispersion is 0.665 vs 0.609. Caveats: capital is deflated by a gross-output
proxy, and the deflated `A_t` uses supplying-industry gross-output indexes
rather than commodity prices.

## Structural outliers

`HS` (Housing) is mostly imputed rent with almost no measured intermediate
cost. `GFGD`, `GFGN`, `GFE`, `GSLG` and `GSLE` are government units, not
capitalist enterprises. Both are kept in the full sample but excluded from the
market-industry subset, which is the headline sample.

## Results, 1998-2023, net basis

- Market general rate of profit `R = S/M`: 20.2% in 2023 with fixed assets +
inventories as `M`, or **10.9%** if `M` includes circulating capital (the
headline Moseley variant); full sample 10.3% and 7.1% respectively.
- Market surplus-value rate on cost `S/K`: 23.8%.
- Market weighted CV of `r_i`: 0.609 in 2023 (sample mean 0.703); p90/p10 6.10.
- Full-sample CV: 2.109 in 2023 (sample mean 2.296), dominated by housing and
  government.
- MAE of `PP` vs gross output: 11.8% full, 10.8% market-only.
- MAE of the long-run `PP*`: 15.4% full, 13.1% market-only.
- MAE of `PP_V` vs gross output: 53.1%.
- Correlation of `PP` with gross output: 0.942 full, 0.990 market-only.
- Share within 25% of `PP`: 88.1% full, 93.1% market-only.
- Proxy sensitivity, full-sample MAE: fixed assets + inventories 12.6%, cost
  13.3%, output 11.0%, value-added 9.0%. Market-only MAE: 13.7%, 10.5%, 8.7%,
  7.1%.
- Sector-deflated real growth, 2005-2023: value added 1.79%/yr, gross output
  1.66%/yr.

Interpretation: in the market sample, actual capital stocks still fit **worse on
average error** than the cost proxy, though the cross-sectional correlation is
high (0.982). The full-sample numbers move because government and housing
capital are now actual and very large relative to their surplus-value. That
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
value of 10.4% and a half-life of about 2.0 years. The error-correction evidence
does not support gravitation: PP adjusts toward market output (β=+0.201,
p=0.004), but market output does not measurably adjust toward PP (β=-0.091,
p=0.239). A
five-year trailing long-run centre shows stronger mean reversion (β=-0.117,
p=0.004) and a 1.8-year half-life. Neither benchmark beats a random walk in
out-of-sample forecasts.

## Next steps

- Replace the broad allocation for mining/utilities/construction and “other”
  industries with detailed inventory data.
- Refine the intermediate-input deflator with commodity-level prices and
  time-varying Use weights.
- Use Make and Use tables to compute labour values via the Leontief inverse.
- Build unit prices by dividing gross output by quantity indices.
