# Reading the figures

This page explains the six "findings" figures in plain language. No economics
or statistics assumed. If you want the arguments in full, read
[`plain_language.md`](plain_language.md) first; this page is just about what the
pictures show and how to look at them.

All six live in `output/figures/` and are named `findings_*.png`. Rebuild them
at any time, without downloading anything:

```bash
.venv/bin/usa-marxian figures
# or
make figures
```

Every figure uses the same colours, so you can track a benchmark across all six:

- **blue** — Moseley (capital stock)
- **green** — Sraffa (simultaneous prices of production)
- **ochre** — Shaikh (the same system reached by iteration)
- **orange** — regulating capital (a Census-based proxy)
- **red** — direct prices (plain labour values)

---

## The three numbers that appear everywhere

Three summary statistics do most of the work in this project. They answer
different questions, and mixing them up is the main source of confusion.

- **Mean absolute error (MAE, in %).** On average, how far off is the model's
  number for an industry, as a share of the observed number? "12%" means the
  model typically misses by about a tenth. Lower is better.
- **Correlation.** Do industries that the model calls expensive actually turn
  out expensive? 1.0 is perfect ordering, 0 means no relation. Higher is better.
- **Slope.** If the model says one industry is 10% above average, how much above
  average is it in the data? 1.0 means "exactly as far". 0.5 means "half as
  far" — the model has the right direction but too little spread. 0 means the
  model's differences tell you nothing.

A high correlation with a low slope is common and meaningful: the model ranks
industries correctly but flattens the differences.

---

## 1. `findings_benchmark_fit.png` — which benchmark tracks revenue best?

**What you are looking at.** Nine versions of "the price an industry should
charge", each compared with that industry's actual sales. The left panel is the
typical miss (MAE); the right panel is how well the ranking matches
(correlation). Bars are sorted best-to-worst.

**What to look for.** The ordering is the same on both panels, and the blue
Moseley bars sit at the top. The gap between the best blue bar (10.4%) and the
labour-value bar (36.5%) is the headline.

**What it means.** A benchmark built from the actual stock of capital firms have
advanced — cost plus the normal profit on that stock — lands closer to observed
industry revenue than benchmarks built from flows of inputs. Treating taxes
separately and including working capital both improve it further.

**What it does not mean.** It is not proof that this is how prices are formed. A
benchmark can fit well simply because it is built from the same cost data that
feeds the observed revenue. The interesting question is the *relative* ranking
of the benchmarks, and that ordering is stable.

---

## 2. `findings_unit_prices.png` — prices per unit, not total sales

**What you are looking at.** Three scatter plots. Each dot is one
industry-year. The horizontal axis is the model's relative price; the vertical
axis is the observed relative price. Both are normalised so the average is one,
so this is about *relative* prices — is steel cheap relative to lawyers? — not
about the overall price level.

The dashed diagonal is perfect agreement. The solid line is the fitted
relationship; its slope is printed in the corner together with the correlation.

**What to look for.** How tightly the cloud hugs the dashed line, and how close
the solid line is to it. Moseley's cloud is the tightest (correlation 0.88) and
its line is steepest (slope 0.60). Sraffa's is looser (0.73, slope 0.46). Direct
labour values are almost a horizontal smear (0.19, slope 0.05).

**What it means.** Once you measure prices per unit rather than total revenue,
Moseley's benchmark still carries real information about relative prices — and
it carries the most. Sraffa and Shaikh have some content but compress the
differences; plain labour values carry almost none.

**What it does not mean.** A slope of 0.60 is not a passing grade. The model
reproduces only about 60% of the observed spread. Measurement error and industry
aggregation both push slopes down, but correcting for them does not close the
gap to one.

---

## 3. `findings_gravitation.png` — do prices actually get pulled toward the benchmark?

**What you are looking at.** Two panels of estimated coefficients, with 95%
confidence bars. Each coefficient asks: when an industry's output was above its
benchmark price last year, what happened next?

- **Left panel** — did market output fall back toward the benchmark?
- **Right panel** — did the benchmark price rise toward market output instead?

**What to look for.** The red dashed line is zero. A bar entirely to the left of
zero means the gap closes on that side; entirely to the right means it widens.

**What it means.** This figure plots the stock-capital Moseley benchmark. For
it, market output does move back toward the benchmark (−0.163, p=0.015), and the
benchmark also moves toward output (+0.105). That is two-way adjustment — slow
gravitation. On the headline working-capital variant the output coefficient
loses significance (−0.091, p=0.239) and only the benchmark adjusts, so the
two-way reading is specific to the stock measure. For Sraffa and
Shaikh the output coefficient is *positive* and significant: industries that
were already expensive grew faster, which is divergence, not gravitation.

**What it does not mean.** These are annual data over 26 years with 65
industries, so "gravitation" here is slow business-cycle adjustment, not a
mechanical law. And a significant coefficient is not a large one: the estimated
half-life of a deviation is about two years.

---

## 4. `findings_forecast.png` — can the benchmark predict the future?

**What you are looking at.** Out-of-sample forecasting error by horizon, for the
stock-capital variant (the working-capital variant gives 0.176 at one year, still
worse than naive). The
models are: do nothing (`naive` — next year looks like this year), an
autoregression (`ar1`), an error-correction model that uses the gap to the
benchmark (`ecm`), and using the benchmark itself as the forecast (`pp`). Lower
is better. The left panel is the current benchmark; the right panel is the
slow-moving five-year version.

**What to look for.** The red line. It is above everything else at every
horizon, on both panels.

**What it means.** Being a good description of where prices sit is not the same
as being a good forecast of where output goes. The price benchmark loses to
simply repeating last year's number — by a wide margin (0.213 against 0.120 at
one year). This is the project's most negative result and it is robust.

**What it does not mean.** It does not refute the theory. Gravitation could be
real and still be useless for forecasting a noisy annual series, especially when
the theory says adjustment is slow.

---

## 5. `findings_dispersion.png` — how unequal are profit rates, and does deflating matter?

**What you are looking at.** Two panels. Left: a measure of how spread out
industry profit rates are, year by year, on a log scale — red for all 71
industries, blue for the 65 market industries. Right: the overall market profit
rate in current dollars (blue) and in constant 2017 dollars (green dashed).

**What to look for.** The vertical gap between red and blue on the left, and the
near-overlap of the two lines on the right.

**What it means.** Left: almost all the apparent dispersion comes from two
non-capitalist outliers — owner-occupied housing and government units. Among
market industries the spread is roughly a third as large (0.61 against 2.11 in
2023). Profit rates are unequal, but not wildly so once you compare like with
like. Right: deflating barely moves the aggregate profit rate (20.2% nominal
against 20.2% real in 2023), which is why the project treats the nominal
comparison as the primary test.

**What it does not mean.** Equal profit rates are not observed. A coefficient of
variation of 0.61 is substantial dispersion, consistent with persistent
industry-specific rents rather than a textbook equalisation.

---

## 6. `findings_capital.png` — what the capital numbers are made of, and how good they are

**What you are looking at.** Two panels of horizontal bars. Left: what the
capital stock the benchmark uses is made of in 2023 — private fixed assets,
government and housing capital, and inventories. Right: the inventory total
split by data source.

**What to look for.** On the left, the government-and-housing bar is the longest
by a wide margin. On the right, the two segments are close to equal — roughly
half the inventory value is detailed, roughly half is allocated.

**What it means.** Left: the project no longer falls back on a cost proxy
anywhere — all 71 industries carry an actual capital stock: 82,746 bn of fixed
assets plus 3,805 bn of inventories, 86,550 bn in total. Of that, 47,797 bn is
government and housing, which is why the full-sample numbers look so different
from the market-only ones: those units hold enormous capital relative to their
surplus. Right: 53.7% of inventory value comes from detailed BEA tables and 46.3%
is still allocated within broad groups. That share is the honest measure of the
remaining data limitation.

**What it does not mean.** "Actual capital" is still a BEA net stock at current
cost, not a Marxian measure of capital advanced. The figure documents data
provenance, not theoretical adequacy.

---

## If you only look at one

Figure 2. It is the cleanest statement of what the project found: with
independent quantity data, the capital-stock benchmark reproduces relative
prices far better than the alternatives, and plain labour values reproduce
almost nothing. Figure 4 is the necessary counterweight — the same benchmark is
worse than a random walk at forecasting.

## A caution that applies to all six

These are measurements on annual US industry data for 1998-2023, built from
public accounts. The figures show how well each benchmark describes that
accounting record. They do not identify causal mechanisms, they do not test
Marx's value theory in the abstract, and they do not speak to firm-level or
product-level competition.
