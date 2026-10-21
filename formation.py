import marimo

__generated_with = "0.25.2"
app = marimo.App(width="full", layout_file="layouts/formation.slides.json")

with app.setup:
    import marimo as mo


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Quantitative analysis

    According to [investopedia](https://www.investopedia.com/articles/investing/041114/simple-overview-quantitative-analysis.asp), *Quantitative analysis uses mathematical models to analyze financial data and develop algorithm-based trading strategies.*

    Correct, but overly specific.

    ## It's a tool to help you get answers to your questions

    - Should I buy AAPL stock?
    - Should I hedge my US dollar exposure?
    - Should I add a short-term mean-reversion strategy overlay to my long-term trend-following strategy?
    - What is the correlation between my portfolio and the S&P 500 index?
    - etc...
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Example situation

    You have a portfolio with 100% in `SPY` (S&P500 ETF).

    You heard yesterday about volatility targeting in your favorite financial podcast, and you want to know if it is a good idea to implement it for you.

    If seasoned professionnals use it, it surely has merits, right?

    ## Volatility targeting definition

    According to [Quantpedia](https://quantpedia.com/an-introduction-to-volatility-targeting/):

    *"The main aim of the volatility targeting technique is to manage the portfolio’s exposure in such a way that the volatility of a portfolio is as close to the target value as possible.*

    *In other words, to ensure that the amount of dollar risk remains the same."*

    But words are still just words, you want to see by yourself the impact of this technique!

    **How can you do that?**
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Know your tools

    Enter Python.

    With it, you can **very** easily obtain the necessary data, perform the necessary calculations, and visualize the results.

    ## Why not use Excel?

    Excel is a great tool, but it has some limitations when it comes to quantitative analysis:

    - It is not designed for large datasets. The hard limit is around 1 millions rows per sheet. You can process **hundreds of millions of rows** with python in a matter of seconds.
    - It can do only a *subset* of what Python can do
    - Once it becomes more complex than a few formulas, it becomes hard to maintain
    - LLMs can interact way more easily with code than with Excel sheets
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Define the problem

    So, you want to get the data for your portfolio, which is 100% in `SPY`, compute the volatility targeting strategy, and visualize/analyze the results.

    First, we want to:

    - download the data
    - save it
    - maybe clean it to our wanted format
    - save it again to a definitive file
    - check that everything is good.

    We'll use the `parquet` file format. Think of it as a **much** better `CSV` file.

    It can be done in a few lines of code.
    """)
    return


@app.cell
def _():
    mo.md(r"""
    # We need a ticker

    To use it's name, and link it to concrete files on disk.

    We'll use `pathlib.Path` to represent file paths, e.g `users/my_folder/my_file.txt`

    We first define a structure, a class, to hold those informations together
    """)
    return


@app.cell
def _():
    from pathlib import Path
    from dataclasses import dataclass
    from typing import Self

    PARQUET = ".parquet"

    @dataclass(slots=True)
    class Ticker:
        name: str
        raw: Path
        clean: Path

        @classmethod
        def from_name(cls, name: str) -> Self:
            raw = Path(f"{name}_raw").with_suffix(PARQUET)
            clean = Path(name).with_suffix(PARQUET)
            return cls(name, raw, clean)

    SPY = Ticker.from_name("SPY")
    SPY
    return SPY, Ticker


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Getting the data

    Now that we have your ticker, we define the downloading steps in themselves.

    - `yfinance` will let us download the data from Yahoo Finance
    - `polars` will let us manipulate said data, save/read it, and do all the computations we need.
    - `plotly` will help us visualize the results.
    """)
    return


@app.cell
def _(SPY, Ticker, self):
    import yfinance as yf
    import polars as pl

    def download_ticker(ticker: Ticker) -> None:
        data = yf.download(self.name, period="max")
        pl.from_pandas(data, include_index=True).write_parquet(self.raw)

    # download_ticker(SPY)
    pl.scan_parquet(SPY.raw).head(5).collect()
    return (pl,)


@app.cell
def _():
    mo.md(r"""
    # Cleaning up data

    Nice, we have our `SPY` prices! But as expected, the format isn't what we want:

    - The column names are weird
    - We don't need the hour/minute/second part of the date
    """)
    return


@app.cell
def _(SPY, Ticker, pl):
    def clean_raw_data(ticker: Ticker) -> pl.LazyFrame:
        return pl.scan_parquet(ticker.raw).select(
            pl.col("Date").cast(pl.Date).alias("date"),
            pl.col(f"('Open', '{ticker.name}')").alias("open"),
            pl.col(f"('High', '{ticker.name}')").alias("high"),
            pl.col(f"('Low', '{ticker.name}')").alias("low"),
            pl.col(f"('Close', '{ticker.name}')").alias("close"),
        )

    clean_raw_data(SPY).head(5).collect()
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    It works, great!

    We see that there's a common structure for the name, and we know that we will probably download again from yfinance, hence always needing to clean immediately afterwards.

    So, we extract this logic in a reusable function, and save our cleaned-up data in a new file.

    Finally, we plot our full data to visualize it (that's what we want, right?) and re-check that everything is good.
    """)
    return


@app.cell
def _(SPY, Ticker, pl, ticker):
    import plotly.express as px
    from plotly.graph_objects import Figure

    def run_clean_up(ticker: Ticker) -> None:
        return (
            pl.scan_parquet(ticker.raw)
            .select(rename_all(ticker.name))
            .sink_parquet(ticker.clean)
        )

    def rename_all(ticker_name: str) -> str:
        prefix = "('"
        suffix = f"', '{ticker}')"
        return (
            pl.col("Date").cast(pl.Date).name.to_lowercase(),
            pl.all()
            .exclude("Date")
            .name.replace(suffix, "", literal=True)
            .name.replace(prefix, "", literal=True)
            .name.to_lowercase(),
        )

    # run_clean_up()

    px.line(
        pl.read_parquet(SPY.clean),
        x="date",
        y="close",
        log_y=True,
        template="plotly_dark",
    )
    return (px,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Getting into it

    Good news, we are done with the **hardest** part now!

    So, let's start computing that volatility targeting strategy.


    Each asset has a mean return and standard deviation of returns, which is also commonly called volatility.

    If our asset has a std of 15% and a mean return of 10%, the implication is the following:

    *in a given year, I can expect that my portfolio performance will end up somewhere between -5% and + 25%*.


    ## The maths

    RiskHub defines volatility targeting with the following formula:

    $$w_t = \frac{\sigma_{\text{target}}}{\hat{\sigma}_t}$$

    Where:
    - $w_t$ is the position weigth, our adjustment factor
    - $\sigma_{\text{target}}$ is our target volatility.
    - $\hat{\sigma}_t$  is the current forecast of the asset's volatility.

    We also define $w_c$ as the current position weight, which is the **current**, actual exposure of our portfolio to SPY.
    """)
    return


@app.cell
def _():
    mo.md(r"""
    ## The Core Idea

    - We want to define our  $\sigma_{\text{target}}$ as a constant annualized volatility of 15%.
    - The volatility forecast $\hat{\sigma}_t$ will be computed on the last 20 days (1 month). This is a common choice.
    - On a given day, sometimes SPY will be higher, or lower. We wan't to act once per day.
    - This means we'll have to buy or sell shares daily to ensure that $w_c$ is as close as possible to $w_t$

    Basically, we want to ensure that the following equality is true as much as possible :

    $$w_t = w_c$$
    """)
    return


@app.cell
def _():
    mo.md(r"""
    ## Example

    If we go from an exposure of $1$, i.e "I have 100 dollars in my portfolio, and they are all in SPY right now", then if `SPY` vol is at:

    - **5%** => We want to buy 200 dollars more to amplify our exposure and reach our target of $3$.
    - **15%** => We do nothing, since $current = target$
    - **30%** => We want to sell half of our shares to reduce our exposure and reach our target of $0.5$.

    Note that this imply access to cheap leverage, which is easy to do with SPY (that's not always the case!)
    """)
    return


@app.cell
def _():
    mo.md(r"""
    ## Forecasting the volatility

    To estimate the volatility, we can simply assume that if today vol is at x, then it's *reasonnable* to expect tomorrow to be more or less in the same ballpark.

    As such, we'll use a 20-day rolling window sample standard deviation of the daily log returns.

    The formula for the window stdev being:

    $s_t = \sqrt{\frac{1}{19}\sum_{i=t-19}^{t}\left(x_i-\bar{x}_t\right)^2}$

    With the arithmetic mean $\bar{x}_t$ as :

    $\bar{x}_t = \frac{1}{20}\sum_{i=t-19}^{t}x_i$


    But first we need to compute our log returns $r_t$ from our raw price data.

    We can define

    $r_t = \ln\left(\frac{P_t}{P_{t-1}}\right)$

    Which then let us continue with our next formula: ...
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ... Or we could go to code where obscure maths signs are replaced by clear english words, shall we?
    """)
    return


@app.cell
def _(SPY, pl):
    def vol_target_from_close(
        lf: pl.LazyFrame, target: float = 0.15
    ) -> pl.LazyFrame:
        log_return = pl.col("close").log().diff().alias("log_return")
        std = (
            log_return.rolling_std(window_size=20, min_samples=20)
            .mul(16)
            .alias("std")
        )
        vol_target = pl.lit(target).truediv(std).alias("vol_target")
        return lf.with_columns(log_return, std, vol_target)

    df = pl.scan_parquet(SPY.clean).pipe(vol_target_from_close).collect()
    df.head(30)
    return df, vol_target_from_close


@app.cell
def _(df, px):
    px.line(
        df,
        x="date",
        y=["std", "vol_target"],
        template="plotly_dark",
    )
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Compute our new returns

    We can now use our `vol_target` to compute our final results.

    For the daily returns, it's as simple as multiplying the `vol_target` of yesterday, $d-1$, by the `pct_return` of today $d$, for each day $d$.

    The cool property of log returns is that they are **additive**: To compute our equity curve, a simple cumulative sum is enough, and it let us directly compare the two strategies.
    """)
    return


@app.cell
def _(SPY, pl, vol_target_from_close):
    def vol_target_returns(lf: pl.LazyFrame) -> pl.LazyFrame:
        vol_target_returns = (
            pl.col("log_return")
            .exp()
            .sub(1)  # Reconvert log return to pct return
            .mul(pl.col("vol_target").shift(1))
            .log1p()  # Re-reconvert pct return to log return
            .alias("vol_target_returns")
        )
        # Drop the nulls, to make both equity curves start at the same point
        return lf.with_columns(vol_target_returns).drop_nulls()

    (
        pl.scan_parquet(SPY.clean)
        .pipe(vol_target_from_close)
        .pipe(vol_target_returns)
        .head(5)
        .collect()
    )
    return (vol_target_returns,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Analyzing the results

    So, now that we have computed our strategy returns, we can analyze the results.

    From this point, it's very easy to compute any statistics we want, and visualize them, to compare against our benchmark.

    If it's not better than the benchmark, why bother implementing it?


    ## Questions to ask yourself

    - How does the equity curves compare?
    - How does the relative performance compare, i.e on a given day, was it better to be in the benchmark or in the strategy?
    - Are the extreme returns more on the upside or downside (skewness)?
    - How much are those extreme returns influencing the strategy (kurtosis)?
    """)
    return


@app.cell
def _(SPY, pl, vol_target_from_close, vol_target_returns):
    STATS_COLS = [
        "bench_equity",
        "strat_equity",
        "bench_drawdown",
        "strat_drawdown",
        "relative_equity",
        "relative_returns",
        "rolling_relative_perf",
        "bench_perf_ratio",
        "strat_perf_ratio",
        "bench_skew",
        "strat_skew",
        "bench_kurtosis",
        "strat_kurtosis",
    ]

    def get_stats(lf: pl.LazyFrame, window: int = 252) -> pl.LazyFrame:
        strat_returns = pl.col("vol_target_returns")
        log_return = pl.col("log_return")
        relative_returns = strat_returns.sub(log_return)
        strat_equity = strat_returns.cum_sum()
        bench_equity = log_return.cum_sum()

        return lf.with_columns(
            strat_equity.alias("strat_equity"),
            bench_equity.alias("bench_equity"),
            relative_returns.alias("relative_returns"),
            relative_returns.cum_sum().alias("relative_equity"),
            relative_returns.rolling_sum(window_size=window).alias(
                "rolling_relative_perf"
            ),
            bench_equity.pipe(_log_equity_dd).alias("bench_drawdown"),
            strat_equity.pipe(_log_equity_dd).alias("strat_drawdown"),
            strat_returns.pipe(_risk_adjusted_returns, window=window).alias(
                "strat_perf_ratio"
            ),
            log_return.pipe(_risk_adjusted_returns, window=window).alias(
                "bench_perf_ratio"
            ),
            log_return.rolling_skew(window_size=window).alias("bench_skew"),
            strat_returns.rolling_skew(window_size=window).alias("strat_skew"),
            log_return.rolling_kurtosis(window_size=window).alias(
                "bench_kurtosis"
            ),
            strat_returns.rolling_kurtosis(window_size=window).alias(
                "strat_kurtosis"
            ),
        )

    def _log_equity_dd(expr: pl.Expr):
        return expr.sub(expr.cum_max()).exp().sub(1)

    def _risk_adjusted_returns(expr: pl.Expr, window: int) -> pl.Expr:
        return expr.rolling_sum(window_size=window).truediv(
            expr.rolling_std(window_size=window).mul(16)
        )

    df2 = (
        pl.scan_parquet(SPY.clean)
        .pipe(vol_target_from_close)
        .pipe(vol_target_returns)
        .pipe(get_stats)
        .select(
            "date",
            *STATS_COLS,
            pl.col("vol_target_returns").alias("strat_returns"),
            pl.col("log_return").alias("bench_returns"),
        )
        .collect()
    )
    return STATS_COLS, df2


@app.cell
def _(STATS_COLS, df2, px):
    px.line(df2, x="date", y=STATS_COLS, template="plotly_dark")
    return


@app.cell
def _(df2, px):
    px.histogram(
        df2.select("strat_returns", "bench_returns"), template="plotly_dark"
    )
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""

    """)
    return


if __name__ == "__main__":
    app.run()
