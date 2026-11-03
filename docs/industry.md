# Industry layer: data, construction and caveats

## Source

BEA input-output archive (keyless):

```
https://apps.bea.gov/industry/iTables%20Static%20Files/AllTablesIO.zip
```

The project parses
`IOUse_After_Redefinitions_PRO_1997-2023_Summary.xlsx`: 27 annual sheets, 71
summary industries, producer prices, after redefinitions.

Extracted fields per industry:

| Field | Meaning |
|---|---|
| `C` | total intermediate consumption |
| `V` | compensation of employees |
| `T` | taxes on production and imports, less subsidies |
| `GOS` | gross operating surplus |
| `N` | total value added |
| `GO` | total industry output |

## Construction

```
S_i = T_i + GOS_i
K_i = C_i + V_i
r_i = S_i / K_i
R_cost = sum(S_i) / sum(K_i)
PP_K_i = K_i (1 + R_cost)
PP_V_i = V_i (1 + sum(S) / sum(V))
```

`S_i` is gross of consumption of fixed capital, because GOS is gross. `R_cost`
is a mark-up on cost, not the macro stock-based profit rate. `PP_K` assumes the
industry capital stock equals its cost price (`M_i = K_i`), which is the main
proxy limitation.

## What the identity does and does not show

The Use table satisfies `C_i + N_i = GO_i` by construction. Therefore a value
price defined as `C_i + N_i` equals observed gross output exactly; a
"value-price vs. observed-price" test at this level is vacuous.

The informative tests are:

1. **Dispersion of `r_i`.** Equalisation predicts low dispersion. The project
   reports the weighted coefficient of variation, p90/p10, and a market-only
   subset.
2. **Price-of-production fit.** `PP_K` and `PP_V` are compared with `GO_i` by
   mean absolute percentage error, correlation, and log-log slope.
3. **Benchmark comparison.** `PP_V` is a labour-only markup; if `PP_K` fits
   much better, capital costs carry information beyond labour costs.

## Structural outliers

`HS` (Housing) is mostly imputed rent with almost no measured intermediate
cost. `GFGD`, `GFGN`, `GFE`, `GSLG` and `GSLE` are government units, not
capitalist enterprises. They remain in the full sample but are excluded from
the market-industry subset. Without that exclusion, the weighted CV is
dominated by Housing.

## Results, 1997-2023

- Latest cost-price mark-up: 38.7%.
- Full-sample weighted CV of `r_i`: 2.14; 2023 p90/p10: 8.72.
- Market-only weighted CV: 0.675.
- MAE of `PP_K` vs gross output: 15.3% full, 14.1% market-only.
- MAE of `PP_V` vs gross output: 45.8%.
- Correlation of `PP_K` with gross output: 0.89.
- Share within 25% of `PP_K`: 84.5% full, 87.2% market-only.

Interpretation: the equalised-profit benchmark tracks gross output much better
than a labour-only markup, but industry surplus-value rates are far from
equalised. The result is consistent with competition plus persistent
industry-specific rents, adjustment costs, and measurement error in the
capital proxy. It is not a decisive test of the transformation procedure.

## Next steps

- Replace `M_i = K_i` with BEA fixed-asset stocks by industry.
- Subtract industry CFC to move from gross to net surplus-value.
- Use Make and Use tables to compute labour values via the Leontief inverse.
- Build unit prices by dividing gross output by quantity indices.
