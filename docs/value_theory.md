# Testing value theory: the MELT against distribution

This page reports the first attempt at testing a substantive claim of the
labour theory of value — not the accounting identities, but the proposition
that the **monetary expression of labour time is determined before
distribution**, so that the division of new value into wages and surplus
cannot move it.

The attempt produced a result about the test rather than about the theory.
That result is worth recording, because it is the same wall anyone hits when
they try to make value theory falsifiable inside national accounts.

Reproduce with:

```bash
.venv/bin/usa-marxian value-tests
# or
make value-tests
```

Outputs: `output/value_theory.json`, `output/tables/melt_concept_spread.csv`.

---

## The claim under test

Moseley's architecture determines surplus-value at the aggregate level, then
derives the general rate of profit `R = S/M`, then prices of production. The
MELT `m` enters earlier still: `N = mL` says new value is money times hours.
The theory's content is that `m` is a property of the monetary system and
productivity — the "value of money" — and **not** of the class struggle.

That is a clean, falsifiable-sounding proposition: regress the growth of `m`
on the growth of the price level, the growth of labour productivity, and the
growth of the wage share. If the wage share matters, the claim is false.

Run on US data, 1950-2024, 74 annual changes:

```
R² = 1.000000        max |residual| = 9.4e-16
coefficients:  const 0.000   Δlog P 1.000   Δlog q 1.000   Δlog wage share 0.000
```

The wage-share coefficient is zero, R² is one, and the residual is at
floating-point noise. The test passes — and it is worthless, for a reason
that can be written down.

## Why the test is empty

Four identities, each verified numerically in the same run:

```
m         = N / L                     definition of the MELT   (dev 0.0)
P         = N / N_real                the NDP deflator
q         = N_real / L                real new value per hour
=> m      = P × q                     exact decomposition      (dev 1.4e-14)
=> V/(mL) = V/N = the wage share      distribution cancels     (dev 1.1e-16)
```

Because `log m ≡ log P + log q` to machine precision (`dev 8.6e-16`), any
regression of `Δlog m` on `Δlog P` and `Δlog q` fits perfectly, and any third
regressor is forced to a zero coefficient with zero residual. The wage share
cannot enter a variable that is defined as the product of two others.

The second identity is the deeper one: `V/(mL) = V/N`. The MELT cancels out
of the wage share algebraically. So no distributional statement in this
framework can depend on `m`, and no distributional fact can test it. The
independence of the MELT from distribution is not an empirical finding; it is
an architectural property of defining `m := N/L`.

## The consequence for the project's own results

The identity `m_real = q` deserves its own line, because it changes how one
existing result should be read.

```
melt_real = m / (NDP deflator) = (N/L) / (N/N_real) = N_real / L
```

**The "real MELT" is exactly real new value per hour — labour productivity.**
Verified to `1.4e-14`.

So the diagnostics reported earlier — ADF p=0.998, KPSS p=0.010, Zivot-Andrews
p=0.904 on real MELT, and the statement that "real MELT behaves like a
unit-root series" — are statements about productivity per hour, not about the
value of money. They are correct as diagnostics and were always going to come
out that way: productivity is trending, so a unit root is not rejected. This
is now flagged in `README.md` and `docs/model.md`.

## What is left that can actually fail

Once the distributional question collapses, one question survives: **is `m` a
well-defined object at all?** If the value of money were a fact, its level
would not depend on which value-added concept or which hours measure you
happen to choose. It does:

```
value-added concept        latest level   growth        vs NDP
melt_gdp                       111.60      5.13%/yr      1.20x
melt_ndp                        93.35      5.05%/yr      1.00x
melt_nnp                        93.22      5.05%/yr      0.99x
melt_nnp_factor                 84.82      5.07%/yr      0.91x

across all eight specifications  26.87-74.61   2.90-5.13%/yr
```

Two different sensitivities, with two different verdicts:

- **The level is not identified.** 1.32x across value-added concepts and 2.78x
  across specifications. The largest jump comes from the CES hours measure
  (74.6), which counts only private hours and therefore divides new value by a
  smaller denominator. That is a coverage decision, not a discovery about money.
- **The growth rate is close to identified.** 5.05-5.13%/yr across concepts —
  a range of eight hundredths of a percentage point. Within the covered hours
  measures the whole specification range is 5.05-5.13%/yr.

The defensible statement is therefore about growth, not level: in this data
the money value of an hour rises about 5% a year, which decomposes into
inflation plus productivity growth, because that is what it is. Any argument
that needs the *level* of the MELT needs a normalisation the accounts cannot
supply.

## What this says, and does not say, about Marx's theory

It does **not** refute the theory. Moseley's reading never claimed the MELT
was independently measurable; it claimed that the money accounts already
express value, and that the aggregate equalities follow from using the same
money magnitudes at both levels of abstraction. The identity audit confirms
the accounts are internally consistent to machine precision. That is a
coherence result.

It **does** say that a whole class of empirical claims cannot be tested this
way. "The MELT is independent of distribution", "the MELT is a monetary
phenomenon rather than a distributional one", "the value of money is not
altered by the class struggle" — all of these are unfalsifiable inside NIPA,
because `m := N/L` builds the independence in. Presenting them as test results
would be exactly the error this project exists to avoid: testing an identity
and calling the pass evidence.

And it says where the falsifiable content actually lives. It is not in the
MELT. It is in:

- **dynamics** — does output adjust toward prices of production, tested in
  `docs/gravitation.md`;
- **distribution** — the value of labour power, which is the natural
  replacement for this test and is described below;
- **forecasting** — does a value benchmark beat a random walk out of sample,
  which it does not.

## What to run instead

Design B closes with a negative result about the test. The replacements, in
the order I would do them:

1. **Value of labour power** — compute hours embodied in the real wage bundle,
   `Λ_t = Σ_c λ_ct C_ct / L_t`, and test whether `Λ_t` is trendless. The
   theory predicts it is historically sticky; the data can contradict that.
   Uses `final_demand.csv` and the labour values already computed.
2. **Value as regulator of price changes** — `Δlog p` on lagged `Δlog λ` with
   industry and year effects. Levels are contaminated by rents; changes are
   not.
3. **Predictive content of λ** — out-of-sample forecasts of prices from `p_t`,
   `λ_t` and both.
4. **Temporal versus simultaneist valuation** — needs historical-cost capital
   stocks, which the downloader does not fetch yet.

Each of these can fail in a way that means something. That is the only
property that makes a test worth running.

---

# Part two: the value of labour power

The value of labour power is the labour time socially necessary to produce the
worker's means of subsistence. That phrase contains three claims of very
different strength:

1. **Accounting** — the wage equals the money value of the customary basket,
   `V = m·Λ·L`, so the wage share equals the basket's labour content per hour.
2. **Custom** — that content is historically sticky, so `Λ` has no trend.
3. **Independence** — `Λ` is a magnitude in its own right, not a restatement of
   the wage share.

Claim (3) decides whether the exercise has content, and it is the one the test
below turns on.

```bash
.venv/bin/usa-marxian labour-power
```

Outputs: `output/value_of_labour_power.json`, `output/tables/volp_panel.csv`.

## Pre-flight

Two feasibility checks had to pass before any of this was worth computing.

- **Coverage.** Labour values exist only for the 65 market industries, and
  housing (imputed rent) is not one of them. The basket covers **83.8%** of
  personal consumption expenditure, and that share is *stable* — 83.6% in 1998,
  83.7% in 2023 — so excluding it does not manufacture a trend.
- **Coherence.** `Σ λ·F / L` is 0.957, 0.954 and 0.956 in 2000, 2010 and 2023,
  and stays within 0.950-0.965 over the whole sample. The 4% shortfall is the
  truncated non-market sector (government and housing production); because it is
  roughly constant it acts as a scale factor rather than a time-varying bias.
  Both series are written to the panel as `coherence` and `coverage_share`.

## Construction

```
λ_t       = l_t (I - A_t)^-1            hours per 2017 dollar, 65 market industries
C_real_t  = C_t / (go_price_t / 100)    consumption in 2017 dollars
Λ_t       = Σ_c λ_ct · C_real_ct / L_t  hours embodied per hour worked
```

The import adjustment scales consumption by (1 − import share) per commodity.
It moves the level down by about 5% and leaves the trend untouched
(+0.22%/yr adjusted against +0.21%/yr unadjusted).

## Result

```
                                  1998     2023      trend
Basket labour content (actual)   0.726    0.768   +0.21%/yr  (p=0.014)
Basket labour content (wage-fin) 0.749    0.694   -0.22%/yr  (p=0.000)
Wage share V / N                 0.654    0.612   -0.24%/yr  (p=0.000)
Wage-financed ratio to share     1.146    1.133   +0.02%/yr  (p=0.555)
Price / labour value of basket   0.873    0.882   -0.02%/yr  (p=0.555)
Consumption / wage bill          0.969    1.107   +0.42%/yr  (p=0.000)
```

Three readings follow.

**Constancy is rejected, but the drift is small.** `Λ` grows 0.21%/yr
(p=0.014, ADF p=0.012), about 5.5% cumulative over 26 years. The strong
"customary subsistence" reading does not hold exactly.

**The drift is not a value-theoretic movement.** A strictly wage-financed
basket — the observed basket rescaled to cost exactly the wage bill — has
labour content falling 0.22%/yr, essentially identical to the wage share's
0.24%. The ratio between the two is flat to **+0.02%/yr (p=0.555)**. It is flat
for a reason that can be written down: `Λ_wage-financed / ω = 1 / (price ÷ value
of the basket)` holds to machine precision (2e-16), so the wage-financed
construction cannot carry information the price-value ratio does not already
have. So the value of labour power is *not separately identified*: it is the
wage share multiplied by a constant. What the test actually measures, then, is
whether the price-value ratio of the basket moves — and over 26 years it does
not. That is a measured result, not an arithmetic identity, and it is the honest
limit of what these accounts can say about the concept.

**What moves the observed wedge is institutional.** `Λ/ω` rises 0.45%/yr, and
the decomposition shows why: consumption spending has risen from 97% to 111% of
the employee compensation bill (+0.42%/yr) while the price-to-value ratio of
the basket is flat (−0.02%/yr, p=0.555). Workers' consumption is increasingly
financed by something other than wages — transfers, property income, mixed
income — and these accounts cannot separate those. The price side is not doing
it.

## What is identified: the price-value gradient

The measurement that does carry information is the level of prices relative to
labour values by final use:

```
consumption   0.872
government    1.108
investment    1.128
exports       1.289
```

Consumption sells about 13% below its labour value; investment, government and
exports sell above it. The ordering holds in **26 of 26 years**. That is the
pattern an equalised profit rate on capital-intensive production predicts:
value is redistributed toward capital-intensive branches and away from
labour-intensive consumption goods.

This is the most theory-consistent result in the whole value-theory exercise,
so it is worth being precise about what it does and does not show. The gradient
is consistent with the transformation mechanism. It is equally consistent with
markups, indirect taxes, trade margins, and the fact that exports are measured
at border prices. Separating those would need commodity-level tax and margin
data, which this project does not have.

## Where the pre-registered prediction failed

Before running this I predicted `Λ` would *fall*, reasoning that real
compensation per hour has lagged productivity since the 1970s. It rose
+0.21%/yr instead.

The reason is instructive rather than embarrassing: I reasoned from wages, but
the basket is financed by more than wages. Consumption spending grew 0.42%/yr
faster than the wage bill, which more than offset the productivity effect. Had
the sign not been pre-registered, the miss would have been invisible — and it
is itself the strongest evidence that the `C/V` wedge is the driving force.

## What this does not say

- It does not refute the theory of the value of labour power. It shows that the
  concept cannot be given an independent empirical magnitude from national
  accounts alone: every available construction either mixes in non-wage income
  or collapses into the wage share.
- It does not explain the falling wage share. The wage share falls 0.24%/yr on
  its own account; this construction adds nothing to that.
- The price-value gradient is a level statement that depends on the MELT as the
  hours-to-dollars converter and on gross-output-based labour values. A
  different normalisation would shift the levels, though not the ordering
  across uses.
