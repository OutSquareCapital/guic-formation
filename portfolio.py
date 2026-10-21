import marimo

__generated_with = "0.25.2"
app = marimo.App(width="full")

with app.setup:
    import marimo as mo
    import yfinance as yf
    import polars as pl
    from dataclasses import dataclass
    from pathlib import Path
    from pyochain import Seq, Iter, Vec
    from enum import auto, StrEnum
    from typing import Self
    import plotly.express as px


@app.cell
def _(PyoIterable, ticker):
    DB_PATH = Path("data")
    PARQUET = ".parquet"
    RAW_DATA = DB_PATH.joinpath("raw").with_suffix(PARQUET)
    CLEAN_DATA = DB_PATH.joinpath("clean").with_suffix(PARQUET)

    class AssetClass(StrEnum):
        Equity = auto()
        Bond = auto()
        Trend = auto()
        Vol = auto()
        Gold = auto()

        def weight(self) -> float:
            match self:
                case self.Equity:
                    return 0.6
                case _:
                    return 0.1

    @dataclass(slots=True)
    class Ticker:
        name: str
        kind: AssetClass

    class Cols(StrEnum):
        Date = auto()
        Ticker = auto()
        High = auto()
        Open = auto()
        Low = auto()
        Close = auto()
        Volume = auto()

        def pl(self) -> pl.Expr:
            return pl.col(self.value)

        @classmethod
        def iter(cls) -> Iter[Self]:
            return Iter(cls)

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

    def download_raw(tickers: PyoIterable[Ticker]) -> None:
        RAW_DATA.parent.mkdir(parents=True, exist_ok=True)
        data = yf.download(
            tickers.iter().map(lambda t: t.name).collect(list),
            period="max",
            multi_level_index=False,
        )
        df = pl.from_pandas(data, include_index=True)
        df.write_parquet(RAW_DATA)
        clean_data(df.lazy(), tickers)

    def clean_data(lf: pl.LazyFrame, tickers: PyoIterable[Ticker]) -> None:

        CLEAN_SCHEMA = pl.Schema(
            {
                Cols.Date: pl.Date,
                Cols.Ticker: tickers.iter()
                .map(lambda t: t.name)
                .collect(pl.Enum),
                Cols.Volume: pl.UInt32,
            }
        )
        indexes = (Cols.Date, Cols.Ticker)
        return (
            lf.rename({Cols.Date.name: Cols.Date})
            .unpivot(
                on=pl.selectors.exclude(Cols.Date),
                index=Cols.Date,
                variable_name="field_ticker",
                value_name="value",
            )
            .with_columns(
                pl.col("field_ticker")
                .str.strip_prefix("('")
                .str.split_exact("', '", 1)
                .struct.rename_fields(("field", Cols.Ticker))
            )
            .unnest("field_ticker")
            .with_columns(
                pl.col(Cols.Ticker).str.strip_suffix("')"),
                pl.col("field").str.to_lowercase(),
            )
            .pivot(
                on="field",
                on_columns=Cols.iter()
                .filter(lambda c: c not in indexes)
                .collect(tuple),
                index=indexes,
                values="value",
            )
            .cast(CLEAN_SCHEMA)
            .sort(Cols.Date, Cols.Ticker, descending=False)
            .sink_parquet(CLEAN_DATA)
        )

    TICKERS = (
        Iter(
            ("ZROZ", AssetClass.Bond),
            ("TLT", AssetClass.Bond),
            ("GLD", AssetClass.Gold),
            ("SPY", AssetClass.Equity),
            ("SPXL", AssetClass.Equity),
            ("VIXY", AssetClass.Vol),
            ("VIXM", AssetClass.Vol),
            ("SVXY", AssetClass.Vol),
            ("DBC", AssetClass.Trend),
        )
        .map_star(Ticker)
        .collect(Seq)
    )
    TICKERS
    return CLEAN_DATA, Cols, TICKERS, download_raw


@app.cell(hide_code=True)
def _(TICKERS, download_raw):
    mo.ui.button(download_raw, value=TICKERS, label="Download Raw Data")
    return


@app.cell
def _(CLEAN_DATA, Cols):
    VOL_LOOKBACKS = Seq(5, 10, 15, 20)
    TREND_LOOKBACKS = (
        Seq(4, 8, 16, 32, 64, 128, 256)
        .iter()
        .combinations(2)
        .filter_star(lambda st, lt: st * 2 != lt)
        .collect(Seq)
    )
    VOL_TRESHOLD = 0.8

    def active_strats(lf: pl.LazyFrame) -> pl.LazyFrame:
        spy_weigth = pl.col("SPY").mul(0.6)
        bench = pl.col("benchmark")
        strat = pl.col("strat")
        strat_leveraged = pl.col("strat_leveraged")
        return (
            lf.select(
                Cols.Date,
                Cols.Ticker,
                Cols.Close.pl()
                .pct_change()
                .over(Cols.Ticker)
                .alias("pct_return"),
            )
            .collect()
            .pivot(
                on=Cols.Ticker,
                index=Cols.Date,
                values="pct_return",
                maintain_order=True,
            )
            .lazy()
            .with_columns(
                _vol_signal("SPY").alias("long_vol_strat"),
                pl.col("DBC")
                .shift(-1)
                .mul(_trend_signal("DBC"))
                .alias("trend_strat"),
            )
            .drop_nulls()
            .select(
                Cols.Date,
                spy_weigth.add(pl.col("TLT").mul(0.4))
                .add(1)
                .log()
                .alias("benchmark"),
                _add_satellites("SPY", 0.6).alias("strat"),
                _add_satellites("SPXL", 0.3).alias("strat_leveraged"),
            )
            .with_columns(
                _adjusted_perf(bench).alias("benchmark_adj_perf"),
                _adjusted_perf(strat).alias("strat_adj_perf"),
                _adjusted_perf(strat_leveraged).alias(
                    "strat_leveraged_adj_perf"
                ),
                bench.cum_sum().alias("benchmark_equity"),
                strat.cum_sum().alias("strat_equity"),
                strat_leveraged.cum_sum().alias("strat_leveraged_equity"),
                strat_leveraged.sub(bench)
                .cum_sum()
                .alias("strat_leveraged_minus_benchmark"),
                strat.sub(bench).cum_sum().alias("strat_minus_benchmark"),
            )
        )

    def _add_satellites(core: str, weight: float):
        satellite_weight = (1 - weight) / 4
        print(
            f"core {core} with weight: {weight}, satellite weight: {satellite_weight}"
        )
        assert weight + 4 * satellite_weight == 1
        return (
            pl.col(core)
            .mul(weight)
            .add(pl.col("GLD").mul(satellite_weight))
            .add(pl.col("TLT").mul(satellite_weight))
            .add(pl.col("long_vol_strat").mul(satellite_weight))
            .add(pl.col("trend_strat").mul(satellite_weight))
            .add(1)
            .log()
        )

    def _adjusted_perf(expr: pl.Expr, lookback: int = 252) -> pl.Expr:
        return expr.rolling_sum(lookback).truediv(expr.rolling_std(lookback))

    def _vol_signal(ticker: str, short_vol: bool = True) -> pl.Expr:
        def _vol_ranked(n: int) -> pl.Expr:
            vol_expr = (
                pl.col(ticker)
                .rolling_std(n)
                .rolling_rank(252)
                .truediv(252)
                .alias(f"vol_{n}")
            )
            return (
                vol_expr.gt(VOL_TRESHOLD)
                .and_(
                    vol_expr.gt(vol_expr.rolling_mean(20)).alias(
                        f"vol_{n}_gt_mean"
                    )
                )
                .alias(f"vol_{n}_mean")
            )

        signal = (
            VOL_LOOKBACKS.iter()
            .map(_vol_ranked)
            .reduce(pl.Expr.add)
            .truediv(VOL_LOOKBACKS.len())
            .alias(f"vol_signal")
        )

        out = pl.col("VIXM").shift(-1).mul(signal)
        if short_vol:
            out = out.add(pl.col("SVXY").shift(-1).mul(signal.neg().add(1)))
        return out

    def _trend_signal(ticker: str) -> pl.Expr:
        def _trend_ratio(st: int, lt: int) -> pl.Expr:
            return (
                pl.col(ticker)
                .rolling_mean(st)
                .gt(pl.col(ticker).rolling_mean(lt))
                .alias(f"trend_{st}_{lt}")
            )

        return (
            TREND_LOOKBACKS.iter()
            .map_star(_trend_ratio)
            .reduce(pl.Expr.add)
            .truediv(TREND_LOOKBACKS.len())
            .alias(f"trend_signal")
        )

    print(TREND_LOOKBACKS)
    df = pl.scan_parquet(CLEAN_DATA).pipe(active_strats).collect()

    def _log_ret_to_pct(expr: pl.Expr) -> pl.Expr:
        return expr.sum().exp().sub(1).mul(100)

    df.select(
        pl.col("strat").pipe(_log_ret_to_pct).alias("strat_return_%"),
        pl.col("benchmark").pipe(_log_ret_to_pct).alias("benchmark_return_%"),
    )
    return (df,)


@app.cell
def _(Cols, df):
    px.line(
        df,
        y=[
            "strat_adj_perf",
            "benchmark_adj_perf",
            "strat_leveraged_adj_perf",
        ],
        x=Cols.Date,
        template="plotly_dark",
    )
    return


@app.cell
def _(Cols, df):
    px.line(
        df,
        y=["strat_equity", "benchmark_equity", "strat_leveraged_equity"],
        x=Cols.Date,
        template="plotly_dark",
    )
    return


@app.cell
def _(Cols, df):
    px.line(
        df,
        y=["strat_minus_benchmark", "strat_leveraged_minus_benchmark"],
        x=Cols.Date,
        template="plotly_dark",
    )
    return


if __name__ == "__main__":
    app.run()
