import marimo

__generated_with = "0.25.2"
app = marimo.App(width="full")

with app.setup:
    import marimo as mo


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Python introduction

    `Python` is a programming language. It let you express *logic* and *computations*, using a structured language.

    Python is great for beginners and financial analysis for two main reasons:

    - It's designed to be written and read, with a syntax as close as possible to natural english language.
    - There are many libraries and frameworks that make it easy to perform complex tasks without reinventing the wheel.

    ## What's a library?

    It's a piece of code, written by someone else, that already solve a problem you might have.

    For example, you don't wan't to write your own code to convert a serie of numbers into a graph, it would require hours of your time, without you even getting into what you wanted to do in the first place with said graph.

    As such, you'll install said library with a **package manager**.

    ## What's a package manager?

    You might have see `pip install` in python tutorials.

    `pip` is the default package manager for python.

    `uv`, mentionned in the README, is an alternative, and has become, since a few years now, the new standard, for many reasons, including speed, easier usage, etc...

    It let you install libraries (also called *dependency*, or *package*), remove them, or perform various other useful tasks for your project very conveniently. Most importantly, if you install uv, you have at the same time installed `python` on your machine, in one step.

    For more informations, see the README.
    """)
    return


@app.cell
def _():
    mo.md(r"""
    # Basic examples
    """)
    return


@app.cell
def _():
    name1 = "Warren"
    surname1 = "Buffet"
    department1 = "goods and services"
    print(f"Info: {name1} {surname1} is in the {department1} department.")

    name2 = "Ray"
    surname2 = "Dalio"
    department2 = "commodities"
    print(f"Info: {name2} {surname2} is in the {department2} department.")
    return


@app.cell
def _():
    def show_member(name: str, surname: str, department: str) -> None:
        print(f"Info: {name} {surname} is in the {department} department.")

    show_member("Warren", "Buffet", "goods and services")
    show_member("Ray", "Dalio", "commodities")
    return


@app.cell
def _():
    from dataclasses import dataclass
    from enum import StrEnum, auto

    class Department(StrEnum):
        GoodsAndServices = "goods and services"
        Technology = auto()
        Financials = auto()
        Commodities = auto()

    @dataclass
    class Member:
        name: str
        surname: str
        department: Department

        def show(self) -> None:
            print(
                f"Info: {self.name} {self.surname} is in the {self.department} department."
            )

    warren = Member("Warren", "Buffet", Department.GoodsAndServices)
    ray = Member("Ray", "Dalio", Department.Commodities)

    warren.show()
    ray.show()
    return Department, Member, ray, warren


@app.cell
def _(Department, Member, ray, warren):
    from pyochain import Seq

    ALL_MEMBERS = Seq(
        warren,
        ray,
        Member("Jim", "Simons", Department.Financials),
        Member("Cathy", "Wood", Department.Technology),
        Member("Charlie", "Munger", Department.GoodsAndServices),
        Member("George", "Soros", Department.Commodities),
        Member("Peter", "Thiel", Department.Technology),
        Member("Carl", "Icahn", Department.Financials),
    )
    ALL_MEMBERS.iter().for_each(Member.show)
    return ALL_MEMBERS, Seq


@app.cell
def _(ALL_MEMBERS):
    def search_member_department(name: str) -> str:
        """Try to find a member by name and return their department, or a not found message if they don't exist."""
        return (
            ALL_MEMBERS.iter()
            .find(lambda m: m.name == name)
            .map(lambda m: f"{name} is in {m.department} department")
            .unwrap_or(f"{name} was not found")
        )

    warren_dep = search_member_department("Warren")
    print(warren_dep)
    sophie_dep = search_member_department("Sophie")
    print(sophie_dep)
    return


@app.cell
def _(ALL_MEMBERS, Department, Member, Seq):
    def filter_members_by_department(department: Department) -> Seq[Member]:
        return (
            ALL_MEMBERS.iter()
            .filter(lambda m: m.department == department)
            .collect(Seq)
        )

    goods_and_services_members = filter_members_by_department(
        Department.GoodsAndServices
    )
    financials_members = filter_members_by_department(Department.Financials)

    print(goods_and_services_members.len())
    goods_and_services_members.iter().for_each(Member.show)
    return


@app.cell
def _(ALL_MEMBERS):
    import polars as pl

    pl.DataFrame(ALL_MEMBERS)
    return (pl,)


@app.cell
def _(ALL_MEMBERS, Department, pl):
    SCHEMA = pl.Schema(
        {
            "name": pl.String,
            "surname": pl.String,
            "department": pl.Enum(Department),
        }
    )
    df = pl.DataFrame(ALL_MEMBERS, schema=SCHEMA)
    df
    return (df,)


@app.cell
def _(df, pl):
    def add_cols(df: pl.DataFrame) -> pl.LazyFrame:
        name_col = pl.col("name")
        return df.lazy().with_columns(
            name_col.str.to_uppercase().alias("name_uppercase"),
            full_name(pl.col("name")),
            name_col.str.len_chars().alias("name_length"),
        )

    def full_name(expr: pl.Expr) -> pl.Expr:
        return expr.add(pl.lit(" ")).add(pl.col("surname")).alias("full_name")

    lf1 = add_cols(df)
    lf1
    return full_name, lf1


@app.cell
def _(lf1):
    lf1.collect()
    return


@app.cell
def _(df, full_name, pl):
    def group_by_department(df: pl.DataFrame) -> pl.DataFrame:
        return (
            df.lazy()
            .group_by("department")
            .agg(full_name(pl.col("name")), pl.len().alias("count"))
            .collect()
        )

    group_by_department(df)
    return


if __name__ == "__main__":
    app.run()
