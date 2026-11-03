# usa_marxian

An empirical skeleton for testing Fred Moseley's **macro-monetary interpretation**
of Marx's theory (*Money and Totality*, Brill 2016, ch. 2) on US macroeconomic
data.

The project downloads public US data without requiring an API key, constructs
the Marxian aggregates, and runs a small set of transparent tests. It is a
starting point, not a finished econometric study.

## The model in one page

Moseley's aggregate accounting is the circuit of money capital applied to the
whole economy:

```
M - C ... P ... C' - M'        M' = M + ΔM
```

In annual flows (his equations 1-15, ch. 2):

```
P = C + N          total value-price = constant capital + new value
N = m L            new value = MELT x labour hours
K = C + V          cost price = constant capital + variable capital
S = P - K = N - V  surplus-value
R = S / M          general rate of profit
PP_i = K_i + R M_i price of production of industry i
```

where `m` is the monetary expression of labour time (MELT), `M` is the stock of
money capital advanced, and `PP_i` are gross annual industry revenues rather
than unit prices.

The two aggregate equalities — total price = total value, and total profit =
total surplus-value — hold simultaneously by construction, because `R` is
defined from the predetermined `S` and the same money capital magnitudes are
used at both levels of abstraction.

## What can and cannot be tested

A blunt but important point: **the core equations are accounting identities**.
Given `m := N/L`, `N = mL` is true by definition. A "test" that total profit
equals total surplus-value is only informative if profit and surplus-value are
measured independently. The project therefore separates three kinds of work:

1. **Construction** — build `C, V, S, N, L, M, m, R` consistently from NIPA and
   fixed-asset data. This is accounting, and the code checks the identities.
2. **Descriptive dynamics** — how do `m`, `S/V`, `M/V` and `R` evolve? Is `m`
   stable? Does `N` grow proportionally to `L`? These are real empirical
   questions with falsifiable answers.
3. **Independent tests** — industry-level prices of production vs. value
   prices, profit-rate equalisation across industries, and the two equalities
   with independently measured profits. These require BEA input-output tables
   and are stubbed on the roadmap.

The default pipeline implements (1) and (2). Treat its output as measurement,
not as proof of the theory.

## Quickstart

Requirements: Python 3.10+ and network access for the first run.

```bash
# with uv (fast)
uv venv --python 3.11
uv pip install -e ".[dev]"

# or with venv/pip
python3 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -e ".[dev]"
```

Run the pipeline:

```bash
.venv/bin/usa-marxian info       # show identities and the series map
.venv/bin/usa-marxian fetch      # download raw series (cached under data/raw)
.venv/bin/usa-marxian analyze    # build accounts, run tests, write artifacts
.venv/bin/pytest                 # offline unit tests
```

Or with `make`:

```bash
make install
make data
make analysis
make test
```

## Data

No key is needed by default:

- **FRED** keyless CSV endpoint (`fredgraph.csv?id=...`) for NIPA aggregates,
  the fixed-asset stock, and BLS employment/hours series.
- **BEA** annual NIPA flat file for alternative NIPA series.
- **BLS** public API v1 for direct BLS series (v2 with a free key).

Optional free keys unlock the official APIs and higher quotas. Copy
`.env.example` to `.env` and fill in what you have:

```bash
cp .env.example .env
```

See `docs/data_sources.md` for the full mapping and the caveats.

## Empirical mapping (net value-added layer)

| Variable | Series | Concept |
|---|---|---|
| `P` | `GDPA` | total value-price (GDP) |
| `C` | `COFC` | consumed constant capital (depreciation) |
| `N` | `GDPA - COFC` | new value (net domestic product) |
| `V` | `A033RC1A027NBEA` | variable capital (compensation of employees) |
| `S` | `N - V` | surplus-value |
| `M` | `K1NTOTL1ES000` + inventories | advanced capital stock |
| `L` | `HOANBS` index x NIPA 2017 benchmark | total labour hours |

Because constant capital appears in both `P` and `K`, it cancels from `S`
(Moseley's "dual significance of constant capital"). A gross-output layer would
raise `C` and `P` together and leave `S` unchanged; that is why the net
value-added layer is enough for the distribution results, though not for
industry-level value magnitudes.

The default hours method is `indexed`: the nonfarm-business hours index
(`HOANBS`, 1947-present) scaled so that 2017 equals NIPA total hours worked.
The alternatives in `config/settings.yaml` are `nipa` (better coverage, ends
2022) and `ces` (private employment times weekly hours, but FRED's weekly-hours
series only starts in 2006).

## Project layout

```
config/            settings.yaml, series.yaml
src/usa_marxian/
  config.py        typed config + series catalog
  data/            FRED, BLS, BEA readers + cache + account builder
  model/           MELT, aggregate equalities, profit-rate decomposition
  analysis/        LTV regression, descriptive tables
  viz/             plots
  pipeline.py      fetch -> accounts -> analysis -> artifacts
  cli.py           `usa-marxian` command
tests/             offline unit tests (network-free except the marked test)
docs/              model derivation and data notes
notebooks/         exploratory notebooks
data/raw           cached downloads (gitignored)
data/processed     raw panel and accounts (gitignored)
output/            tables, figures, report.json (gitignored)
```

## Outputs

After `analyze`:

- `data/processed/raw_panel.csv` — annual raw series
- `data/processed/accounts.csv` — derived Marxian accounts
- `output/report.json` — headline estimates
- `output/tables/summary.csv`, `ltv_test.csv`, `ltv_test_nominal.csv`,
  `melt_summary.csv`, `melt_summary_real.csv`, `profit_rate_summary.csv`,
  `profit_rate_decomposition.csv`
- `output/figures/melt.png`, `melt_real.png`, `distribution.png`,
  `rate_of_profit.png`, `composition.png`

## First run (data vintage of November 2026)

Sample 1948-2024 (the fixed-asset stock lags NIPA flows by one year):

- nominal MELT: mean 28.5 USD/hour, trend +5.1%/year
- real MELT (2017 USD): 18.9 USD/hour in 1948, 74.3 in 2024
- rate of surplus-value: 0.69 in 1948, 0.63 in 2024
- general rate of profit: 33.9% in 1948, 24.0% in 2024 (mean 23.2%)
- LTV regression on real new value: slope 2.24 (95% CI 2.08-2.40), so the
  unit-slope restriction is rejected — real new value per hour grew over the
  sample, which is exactly what a rising MELT or labour productivity implies.

These numbers are descriptive. They are not a test that "proves" the theory;
see the section above on what is and is not identified.

## Roadmap

1. **Gross-output layer.** Add BEA input-output tables to measure `C` as
   intermediate consumption plus CFC and to compute sectoral value prices.
2. **Industry prices of production.** Use the BEA IO use table to build
   `K_i`, `M_i`, and test `PP_i = K_i + R M_i` and profit-rate equalisation.
3. **Independent profit measures.** Compare `S = N - V` with property income
   (corporate profits + net interest + rent + proprietors' income) to make the
   profit = surplus-value equality informative rather than definitional.
4. **Alternative MELT measures.** Moseley's own estimates use different
   numerators (NNP, NDP, net national income); the module already supports
   swapping the numerator.
5. **Deflation and real magnitudes.** Add a proper value-added deflator and
   compute real MELT and productivity series.
6. **Econometrics.** Accumulation regressions, profit-rate trends with
   structural breaks, and panel tests across industries.

## Reference

Moseley, Fred. 2016. *Money and Totality: A Macro-Monetary Interpretation of
Marx's Logic in Capital and the End of the 'Transformation Problem'*. Leiden:
Brill. Chapter 2 is the algebraic summary used here; the PDF is in the project
root as `money_and_totality.pdf`.

## License

MIT for the code. The book PDF is the user's own copy and is not covered by
this license.
