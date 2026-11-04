# How to read the model: demand closure and slopes

This note explains two ideas that are easy to mix up:

1. **Closing the demand side** — where demand comes from in the stock-flow model.
2. **The slope** — what the number in the unit-price tables means.

They answer different questions. Demand closure is about quantities and flows.
The slope is about prices.

---

## 1. What “closing the demand side” means

### The idea in one sentence

An economy is a circular flow: what one industry produces must be bought by
someone — other industries, households, investors, the government, or foreigners.

A model is **closed** when it determines that demand inside the model instead of
being handed the answer.

### The old version: demand was handed in

The earlier stock-flow model computed final demand as a residual:

```
F_t = q_t − A_t q_t
```

In words:

- `q_t` is how much each industry actually produced.
- `A_t q_t` is how much of each industry’s output other industries used as inputs.
- The difference is “whatever was left over” — final demand.

That is an **accounting residual**, not a behavioural explanation. The model was
told exactly how much final demand each industry faced. It could not ask what
would happen if consumers bought more cars, or if imports fell.

### The new version: demand is built from components

The BEA Use table publishes final demand by category:

```
C  personal consumption
I  private investment (including inventory change)
G  government spending
X  exports
M  imports
```

The model now builds demand as:

```
D_i = Σ_j A_ij q_j  +  C_i  +  I_i  +  G_i  +  X_i  −  M_i  +  residual_i
```

In words, for industry `i`:

- **intermediate demand** — what other industries need from `i`;
- **consumption** — what households buy from `i`;
- **investment** — what firms buy from `i` to expand capacity;
- **government** — what government buys from `i`;
- **exports** — what foreigners buy from `i`;
- **imports** — what is supplied from abroad rather than by `i`, so it is
  subtracted;
- **residual** — a small “everything else” term.

Then output adjusts toward demand:

```
q_i' = q_i + β (D_i − q_i)
```

If demand is above current output, output rises; if demand is below, output
falls. `β` controls how fast.

### What the residual is

The residual is not a behavioural part of the model. It absorbs:

- differences between the Use-table final-demand concepts and the fixed-asset
  investment series;
- inventory changes and statistical discrepancies;
- trade and transport margins;
- measurement differences between the input-output tables and the national
  accounts.

It is about **8% of output** at the base year. That is large enough to report as
a limitation. A truly closed model would explain or eliminate it.

### What “closing demand” buys you

It lets you ask questions like:

- What happens if household demand for one industry rises?
- What happens if imports fall?
- Do demand shocks or price/profit signals dominate output adjustment?
- Does a demand shock to construction spread to other industries?

The model is now suitable for **direction-of-effect** experiments. It is not
ready for quantitative policy analysis.

### Why the fit got worse

The old model was fitted with the observed final-demand residual handed to it.
The new model has to generate demand from components and simulated investment.
That is harder. Quantity and capital still track the data, but less tightly:

```
old: quantity 0.108, capital 0.237
new: quantity 0.197, capital 0.356
```

That is the trade-off between a better accounting fit and a more structural
model.

---

## 2. What the slope means

### The short version

The slope answers:

> If the model says industry A’s price is 10% above average, how much above
> average is A’s observed price?

- **Slope 1** — proportional: 10% in the model means 10% in the data.
- **Slope 0.5** — half as large: 10% in the model means about 5% in the data.
- **Slope 0** — no relation: the model’s price differences say nothing about
  observed price differences.
- **Negative slope** — the model ranks prices in the opposite direction.

### How it is computed

For each benchmark, we estimate:

```
log(observed relative price) = constant + slope × log(model relative price)
```

Both prices are normalised to a weighted average of one, so the comparison is
about **relative** prices, not price levels.

The slope is not a percentage and not an elasticity of demand. It is the
steepness of the line relating model prices to observed prices.

### Correlation vs slope

These are different:

- **Correlation** asks: do the model and data move in the same direction?
- **Slope** asks: how large are the model’s price differences compared with the
  data’s?

You can have a high correlation and a low slope. That means the model ranks
industries correctly but compresses the differences — it says “A is more
expensive than B” but not by enough.

### Why the slope can be low even when the model is useful

1. **The model’s price variation is too small.** If the model produces only half
   the observed spread, the slope is about 0.5 even with a perfect ranking.
2. **Measurement error in observed prices.** If the observed price is noisy, the
   slope is pulled toward zero. This is called attenuation.
3. **Aggregation.** Industry prices are averages; firm and product prices vary
   much more.
4. **Missing cost components.** If the model omits a cost that matters, its
   relative prices will be too flat.

### Current slopes

Unit-price regressions, 2005–2023:

```
Moseley                    0.47
Moseley profit-rate        0.52
Moseley working-capital    0.60
Sraffa                     0.28
Shaikh                     0.31
Regulating                 0.28
Direct prices              0.06
```

Moseley has the steepest slope and the highest correlation. Working-capital
Moseley reproduces about 60% of the observed relative-price spread. Sraffa and
Shaikh rank prices moderately well but compress the differences. Direct labour
values have almost no relation to observed relative prices.

### What would raise the slope

- better industry-level price data (we now use 71-industry BEA indexes);
- less aggregation (firm or product prices);
- correcting for measurement error;
- adding missing cost components;
- allowing markup or regulating-capital heterogeneity.

A low slope is evidence that the model’s relative prices are too flat. It is not
by itself evidence that the model is useless: correlation and slope answer
different questions.

---

## 3. How the two ideas fit together

- **Demand closure** is about the quantity side: who buys what, and how output
  responds.
- **The slope** is about the price side: how strongly model relative prices
  match observed relative prices.
- A model can close demand well and still have flat relative prices, or have good
  relative prices and a poor demand block. The project reports them separately
  for that reason.

## Glossary

- **Final demand**: demand for finished goods, not intermediate inputs.
- **Intermediate demand**: demand from other industries for inputs.
- **Residual**: the part of demand not explained by the modelled components.
- **Exogenous**: taken from the data, not explained by the model.
- **Endogenous**: explained inside the model.
- **Relative price**: a price divided by the average price level.
- **Slope**: how much observed relative price changes when model relative price
  changes by one unit in logs.
- **Attenuation**: the tendency of a noisy explanatory variable to produce a
  slope closer to zero.
