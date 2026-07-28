# Weekly 20-Day Momentum Rotation Strategy

## Purpose

This is the project's selected **long-only swing strategy**. It is a
portfolio-rotation model, not an intraday breakout system and not a strategy
that trades every NIFTY 200 stock at once.

Each week it looks across the NIFTY 200 universe, finds stocks that are both
in a long-term uptrend and stronger than they were 20 trading sessions ago,
then holds only the highest-ranked few stocks. The current model name in code
is **Weekly 20-day relative-strength rotation**.

The strategy is paper-only by default. `run_swing_rotation_targets.py` creates
a target basket; it does not place any broker order.

## What the strategy measures

For every stock, the daily feature calculation creates the following key
values:

```text
RS20 = (today's close / close 20 trading sessions ago) - 1
```

`RS20` is the 20-session price return. For example, an `RS20` of `0.12` means
the stock closed 12% higher than it did 20 sessions earlier.

The selected strategy uses only these three conditions:

1. `RS20 > 0` - the stock has positive 20-session momentum.
2. `Close > SMA50` - price is above its medium-term trend average.
3. `SMA50 > SMA200` - the medium-term trend is above the long-term trend.

Stocks that do not meet all three conditions are excluded. The remaining
stocks are ranked from highest to lowest `RS20`; the top ranks become the
target basket.

Although the feature module also calculates EMA, RSI, ATR, ADX, Bollinger
Bands, volume averages, and other momentum windows, those indicators are **not
entry filters for this specific strategy**. They are available for other
research strategies in the project.

## When it runs

Run the target generator after the Indian market closes on Friday, normally
after **15:45 IST**:

```bash
python3 run_swing_rotation_targets.py
```

Why Friday:

- The ranking is based only on a completed daily candle.
- The Friday close gives a stable weekly decision point.
- The script refreshes the most recent daily candles when run after the Friday
  close, so an incomplete intraday daily candle is not used.

The signal must never be traded at the same Friday close that created it. The
backtest schedules the rebalance for the **next trading session's open**
(normally Monday). This avoids look-ahead bias: Friday's final close was not
known until Friday's market had ended.

On non-Friday days, the script can display a current ranking with:

```bash
python3 run_swing_rotation_targets.py --show-any-day
```

That is for inspection only; it is not a scheduled rebalance signal.

## How portfolio rotation works

At each Friday decision point:

1. Calculate the eligible NIFTY 200 stocks using the rules above.
2. Rank all eligible stocks by `RS20`.
3. Keep only the first `MAX_OPEN_POSITIONS` symbols.
4. On the next session's open, exit holdings that are no longer in the target
   list and buy target symbols not already held.
5. Retain a stock if it remains in the target list; it is not sold and bought
   again merely because its rank changed.

The default configuration is:

```env
MAX_OPEN_POSITIONS=5
MAX_POSITION_VALUE_PCT=0.20
```

Each new position receives the smaller of:

- `MAX_POSITION_VALUE_PCT` of portfolio equity, or
- an equal share of the portfolio (`1 / MAX_OPEN_POSITIONS`).

With the defaults, this is a maximum 20% allocation per position and a maximum
of five simultaneous holdings. Update those values in `.env` if you want a
different number of holdings or allocation cap.

## Exit rule and the meaning of "no stops"

The validated version is called **Weekly 20-day momentum, no stops**.

It has no ATR initial stop-loss and no trailing stop-loss. A position normally
exits only when it is absent from the following weekly target basket, or at the
end of a research period.

This is intentional in the current implementation, but it is a significant
risk characteristic:

- It allows a strong trend to continue without a tight stop removing it.
- It can also tolerate large temporary losses before the next weekly review.
- It is unsuitable for money that cannot tolerate meaningful drawdowns.

Do not interpret "no stops" as no risk management. The position-count and
allocation caps still apply, but they do not guarantee a maximum loss.

## Costs used in research

The portfolio backtest applies the configuration values below when simulating
entries and exits:

```env
SLIPPAGE=0.0005
BROKERAGE_PER_ORDER=20
```

`SLIPPAGE=0.0005` is 0.05%: it worsens a buy price and worsens a sell price.
The backtest also charges brokerage on entry and exit. These assumptions are
useful for research, but actual FYERS charges, taxes, spreads, liquidity, and
opening gaps can differ.

## Output file

The Friday command writes:

```text
reports/swing_rotation_targets.csv
```

### Stateless Docker deployment (optional)

When the scan and stream run in separate containers, set these non-secret
values in the EC2 `.env` file:

```env
S3_BUCKET=fyers-tradebot-state-tara-2026
S3_TARGETS_KEY=state/swing_rotation_targets.csv
```

The Friday scanner uploads the completed basket to this private location. The
stream downloads it at startup and fails rather than silently using an
image-local or stale CSV if S3 cannot be reached. The EC2 instance profile
must allow `s3:GetObject`, `s3:PutObject`, and `s3:ListBucket` for this
location. No AWS access keys are stored in `.env`.

Its important columns are:

| Column | Meaning |
| --- | --- |
| `Rank` | Momentum rank within eligible stocks; 1 is strongest. |
| `Symbol` | Yahoo-format symbol used by the strategy, such as `TCS.NS`. |
| `AsOf` | Completed daily session used for the ranking. |
| `Close` | Closing price on that completed session. |
| `RS20Pct` | 20-trading-session return, expressed as a percentage. |
| `SMA50`, `SMA200` | Trend filters used by the strategy. |
| `MaxAllocationPct` | Maximum planned allocation to a new position. |

This file is a **target list**, not proof that an order was filled. Before any
paper or live action, verify that data refresh completed without errors and
that the target date is the intended Friday close.

## FYERS WebSocket relationship

The FYERS Data WebSocket is optional monitoring infrastructure. After this
strategy generates a target CSV, run:

```bash
python3 run_fyers_stream.py
```

The stream monitors the current target symbols and prints live prices. It does
not alter rankings, create a new signal, or place orders. The weekly ranking
remains based on completed daily candles, not intraday ticks.

## Relevant code

- `strategy/swing_features.py` - calculates `RS20`, SMA values, and other
  daily features.
- `strategy/momentum_rotation.py` - applies the eligibility filters, ranking,
  and allocation calculation.
- `run_swing_rotation_targets.py` - generates the Friday target CSV.
- `backtest/momentum_rotation.py` - simulates weekly next-open rotation,
  costs, position limits, and research exits.
- `run_momentum_rotation_five_year_validation.py` - validates the fixed
  weekly 20-day, no-stop version over five years.

## Important limitations

Past backtest profitability does not guarantee future returns. The model can
underperform for extended periods, and a weekly no-stop strategy can experience
large drawdowns between rebalances. Keep it in paper trading until its current
data, execution assumptions, and risk are acceptable to you.
