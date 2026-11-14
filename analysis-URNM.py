import marimo

__generated_with = "0.25.2"
app = marimo.App(width="full", layout_file="layouts/analysis-URNM.slides.json")

with app.setup:
    import marimo as mo
    from dataclasses import dataclass
    from pathlib import Path
    from typing import Self
    import polars as pl
    import yfinance as yf
    from pyochain import Seq
    import plotly.express as px


@app.cell(hide_code=True)
def _():
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

    SPY = Ticker.from_name("URNM")
    SPY

    def run_clean_up(ticker: Ticker) -> None:
        return (
            pl.scan_parquet(ticker.raw)
            .select(rename_all(ticker.name))
            .sink_parquet(ticker.clean)
        )

    def rename_all(ticker_name: str) -> str:
        prefix = "('"
        suffix = f"', '{ticker_name}')"
        return (
            pl.col("Date").cast(pl.Date).name.to_lowercase(),
            pl.all()
            .exclude("Date")
            .name.replace(suffix, "", literal=True)
            .name.replace(prefix, "", literal=True)
            .name.to_lowercase(),
        )

    def clean_raw_data(ticker: Ticker) -> pl.LazyFrame:
        return pl.scan_parquet(ticker.raw).select(
            pl.col("Date").cast(pl.Date).alias("date"),
            pl.col(f"('Open', '{ticker.name}')").alias("open"),
            pl.col(f"('High', '{ticker.name}')").alias("high"),
            pl.col(f"('Low', '{ticker.name}')").alias("low"),
            pl.col(f"('Close', '{ticker.name}')").alias("close"),
        )

    def download_ticker(ticker: Ticker) -> None:
        data = yf.download(ticker.name, period="max")
        pl.from_pandas(data, include_index=True).write_parquet(ticker.raw)

    px.line(
        pl.read_parquet(SPY.clean),
        x="date",
        y="close",
        log_y=True,
        template="plotly_dark",
    )
    return (SPY,)


@app.cell
def _(SPY):
    def normalize(expr: pl.Expr):
        return pl.col("log_return").mul(expr.shift(1))

    def risk_adjusted_returns(expr: pl.Expr, window: int) -> pl.Expr:
        return expr.rolling_sum(window).truediv(
            expr.rolling_std(window).mul(16)
        )

    def signal(window: int) -> pl.Expr:
        return (
            pl.col("log_return")
            .rolling_sum(window)
            .gt(0)
            .cast(pl.Int8)
            .alias("roc")
        )

    def log_equity_dd(expr: pl.Expr):
        return expr.sub(expr.cum_max()).exp().sub(1)

    def mean_reversion(window: int, bound: int) -> pl.Expr:
        expr = pl.col("log_return").rolling_sum(window)
        return (
            expr.sub(expr.rolling_mean(252, min_samples=252))
            .truediv(expr.rolling_std(252, min_samples=252))
            .mul(-1)
            .clip(-bound, bound)
            .eq(bound)
            .cast(pl.Int8)
            .alias("mr")
        )

    X = Seq([32, 64, 128, 256])
    LENGTHS = (
        X.iter()
        .map(lambda window: signal(window).alias(f"signal_{window}"))
        .reduce(lambda col1, col2: col1.add(col2))
        .truediv(X.len())
    )
    Y = Seq([4, 8, 16, 32])
    LENGTHS_MR = (
        Y.iter()
        .map(
            lambda window: mean_reversion(window, 1).alias(
                f"signal_mr{window}"
            )
        )
        .reduce(lambda col1, col2: col1.add(col2))
        .truediv(Y.len())
    )
    COLS = Seq("benchmark", "strat", "strat_mr", "composite_equity")
    df10 = (
        pl.scan_parquet(SPY.clean)
        .with_columns(pl.col("close").log().diff().alias("log_return"))
        .with_columns(
            pl.col("log_return")
            .rolling_std(window_size=20, min_samples=20)
            .mul(16)
            .alias("std"),
            LENGTHS.alias("signal"),
            LENGTHS_MR.alias("signal_mr"),
        )
        .with_columns(
            pl.col("signal")
            .add(pl.col("signal_mr"))
            .truediv(2)
            .alias("composite")
        )
        .drop_nulls()
        .with_columns(
            pl.col("signal").pipe(normalize).cum_sum().alias("strat"),
            pl.col("signal_mr").pipe(normalize).cum_sum().alias("strat_mr"),
            pl.col("composite")
            .pipe(normalize)
            .cum_sum()
            .alias("composite_equity"),
            pl.col("log_return").cum_sum().alias("benchmark"),
        )
        .with_columns(
            COLS.iter().map(
                lambda c: pl.col(c).pipe(log_equity_dd).alias(f"{c}_drawdown")
            )
        )
        .collect()
    )
    df10
    return COLS, df10, log_equity_dd


@app.cell
def _(df10):
    px.line(
        df10,
        x="date",
        y=["strat_mr", "strat", "benchmark", "composite_equity"],
        template="plotly_dark",
    )
    return


@app.cell
def _(df10):
    px.line(
        df10,
        x="date",
        y=["signal_mr", "signal", "composite"],
        template="plotly_dark",
    )
    return


@app.cell
def _(COLS, df10):
    px.line(
        df10,
        x="date",
        y=COLS.iter().map(lambda c: f"{c}_drawdown").collect(list),
        template="plotly_dark",
    )
    return


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
def _(log_equity_dd):
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
            bench_equity.pipe(log_equity_dd).alias("bench_drawdown"),
            strat_equity.pipe(log_equity_dd).alias("strat_drawdown"),
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

    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""

    """)
    return


if __name__ == "__main__":
    app.run()
