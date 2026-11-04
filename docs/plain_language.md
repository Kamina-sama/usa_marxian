# A plain-language guide

This page explains the project without assuming economics or statistics. The
technical details are in `README.md` and the other documents in `docs/`.

For two terms that are easy to mix up — **closing the demand side** and **the
unit-price slope** — see [`reading_the_model.md`](reading_the_model.md).

## The question

Marx argued that the value of goods comes from the labour used to produce them.
A classic objection is that prices do not seem proportional to labour: some
industries are much more profitable than others. Marx's "transformation problem"
is the attempt to reconcile labour values with observed prices.

Fred Moseley's interpretation says the reconciliation is simpler than usually
thought. Capitalists advance money, production creates new value, and the
surplus is divided across industries by competition. Moseley's claim is that the
aggregate accounts hold exactly, and that industry "prices of production" are
centres around which market prices gravitate.

This project asks: **does that story fit US data?**

## The accounting, in words

For the whole economy in one year:

- **Output (P)** = the money value of everything produced.
- **Used-up capital (C)** = machines and inputs used up in production. In the
  simplest version, this is depreciation.
- **New value (N)** = output minus used-up capital. It is the value created by
  this year's labour.
- **Wages (V)** = what workers are paid.
- **Surplus (S)** = new value minus wages. This is the pool that profits, rents,
  interest and taxes come from.
- **Capital advanced (M)** = the stock of machines, buildings and inventories
  used in production.
- **Profit rate (R)** = surplus divided by capital advanced.

Moseley adds one more idea:

- **MELT (m)** = the money value of one hour of labour, so that
  **new value = m × hours worked**.

And for each industry:

- **Price of production** = the industry's cost plus the normal profit on the
  capital it uses.

The accounting identities are true by construction. For example, if you define
the MELT as new value divided by hours, then "new value = MELT × hours" is a
tautology. That is why the project separates accounting from testing.

## What the project actually does

1. Downloads public US data: national accounts, industry input-output tables,
   fixed assets, inventories, employment, hours, wages and prices.
2. Builds the Marxian accounts at the whole-economy and 71-industry levels.
3. Checks the accounting identities.
4. Compares three kinds of price benchmark:
   - **Moseley**: cost plus profit on the stock of capital.
   - **Sraffa**: a simultaneous "prices of production" system.
   - **Shaikh**: the same system reached by an adjustment process.
5. Compares each benchmark with observed **revenues** and observed **unit
   prices**.
6. Tests whether market prices move toward the benchmark over time
   ("gravitation").
7. Tests whether the benchmark helps forecast future prices or output.
8. Checks robustness: different definitions of capital, hours, wages and
   deflators.

## What we found, plainly

### Revenue fit

Comparing industry revenues with the benchmark:

- Moseley: average miss about **12%**.
- Sraffa: about **19%**.
- Shaikh: about **19%**.
- Direct labour values: about **37%**.

Moseley's benchmark is closest to observed revenues. The other benchmarks are
not disastrous, but they are worse.

### Unit-price fit

Revenue is total market size. Unit price is price per item. When we compare
relative unit prices:

- Moseley `PP/Q`: correlation **0.79**, slope **0.47**.
- Moseley profit-rate `PP/Q`: correlation **0.82**, slope **0.52**.
- Moseley working-capital `PP/Q`: correlation **0.88**, slope **0.60**.
- Sraffa: correlation **0.63**, slope **0.28**.
- Shaikh: correlation **0.67**, slope **0.31**.
- Direct labour values: correlation **0.19**, slope **0.06**.

Here `Q` is the BEA quantity index, not revenue divided by observed price. With
independent quantities, Moseley's unit-price fit is genuine; working-capital
Moseley is the best benchmark.

Correlation measures direction: 0.79 means the model ranks industries fairly
well. Slope measures size: 0.47 means the model's price differences are only
about half as large as observed ones. Direct labour values barely track relative
prices at all.

### Gravitation

Does market output move toward the benchmark when it is away from it?

- Moseley: weak movement in the expected direction.
- Sraffa and Shaikh: the estimated movement is in the **wrong direction** — high
  relative output predicts higher future output, which is divergence.
- None of the benchmarks beats a simple "next year will be like this year"
  forecast.

### Forecasting

No benchmark predicts future prices or output better than a random walk. The
models are useful for understanding accounting and relative prices, not for
forecasting.

## What the numbers mean

- **MAE (mean absolute error)**: the average size of the miss, in percent. Lower
  is better.
- **RMSE**: like MAE, but punishes large misses more. Lower is better.
- **Correlation**: do the model and the data move in the same direction? From
  -1 to +1. Higher is better.
- **Slope**: if the model price is 10% above average, how much above average is
  the observed price? A slope of 1 is proportional; 0.5 means half as much; 0
  means no relation.
- **Beta in the gravitation tables**: how fast a gap closes. Negative means the
  gap shrinks; positive means it grows. This is not a price elasticity.

## What we can and cannot say

We can say:

- the accounting construction is internally consistent;
- Moseley's benchmark tracks revenues and unit prices better than the
  alternatives, especially with working capital included;
- Sraffa and Shaikh have some real relative-price content;
- direct labour values, by themselves, do not.

We cannot say:

- that the labour theory of value is proven;
- that every industry's price equals its labour value;
- that the model captures firm-level or product-level competition;
- that the benchmarks forecast better than a random walk.

## The one-paragraph summary

The accounting identities hold, as they must. Moseley's stock-based benchmark
fits observed industry revenues best and has the strongest unit-price
correlation. Sraffa's and Shaikh's flow-based benchmarks are worse but still
capture some relative-price variation. Direct labour values perform poorly.
Gravitation is weak, and for Sraffa and Shaikh the estimated direction is wrong.
The honest conclusion is that prices of production have empirical content, but
the strong claim that they are centres of gravitation is not supported by this
data.

## Demand closure and slopes

The stock-flow model now builds demand from consumption, investment, government,
exports and imports instead of being handed a residual. That is what “closing
the demand side” means. It also reports a **slope** for each price benchmark:
how much of the observed relative-price spread the model reproduces.

Both ideas are explained in plain language in
[`reading_the_model.md`](reading_the_model.md).

## Glossary

- **Constant capital (C)**: machines, buildings and inputs used up in
  production.
- **Variable capital (V)**: wages.
- **Surplus-value (S)**: new value minus wages.
- **MELT**: the money value of one hour of labour.
- **Capital advanced (M)**: the stock of capital tied up in production.
- **Rate of profit (R)**: surplus divided by capital advanced.
- **Price of production**: cost plus a normal profit on capital.
- **Gravitation**: the tendency of market prices to move toward prices of
  production.
- **Deflator**: a price index used to convert current dollars into constant
  dollars.
- **Input-output matrix (A)**: a table showing how much of each industry's
  output is used by every other industry.
- **Labour values**: the total labour directly and indirectly required to
  produce a good.
