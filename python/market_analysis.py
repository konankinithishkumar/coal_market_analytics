"""
Coal Market & Supply Analytics - end-to-end pipeline
====================================================

Run from the project root:

    python python/market_analysis.py

Steps
-----
1. Load the raw CSV files (data/raw/)
2. Validate them (data/processed/data_quality_report.csv)
3. Calculate market, trade and price metrics (data/processed/*.csv)
4. Draw the charts (outputs/*.png)
5. Write an auto-generated findings summary (outputs/key_findings.md)

Unit rule: production is in million tonnes (Mt); consumption and trade are in
exajoules (EJ). The two are never subtracted from each other. Production and
consumption are compared through growth rates / indices (unit-free), and trade
is compared to consumption because both are in EJ.
"""
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs"

BASE_YEAR = 2014
RECENT_YEAR = 2019          # start of the "recent 5-year" window
OUTLIER_YOY_PCT = 40        # YoY moves larger than this are flagged for review
LOW_BASE_MT = 5             # production below this makes YoY % unreliable
SHARE_SPREAD_TOL = 0.02     # max relative spread of implied world-trade totals

COLORS = {
    "China": "#C0392B", "India": "#E67E22", "Indonesia": "#27AE60",
    "Australia": "#2980B9", "Japan": "#7F8C8D",
}


# --------------------------------------------------------------------------
# 1. LOAD
# --------------------------------------------------------------------------
def load_raw():
    return {
        "production": pd.read_csv(RAW / "coal_production_ei_2014_2024.csv"),
        "consumption": pd.read_csv(RAW / "coal_consumption_ei_2014_2024.csv"),
        "trade": pd.read_csv(RAW / "coal_trade_selected_2023_2024.csv"),
        "prices": pd.read_csv(RAW / "coal_price_worldbank_2021_2025.csv"),
        "price_detail": pd.read_csv(RAW / "coal_price_detail_worldbank.csv"),
    }


# --------------------------------------------------------------------------
# 2. VALIDATE
# --------------------------------------------------------------------------
def validate(d):
    """Return a DataFrame of checks: Dataset, Check, Status (PASS/WARN/FAIL), Detail."""
    rows = []

    def add(dataset, check, status, detail=""):
        rows.append({"Dataset": dataset, "Check": check, "Status": status, "Detail": detail})

    # --- completeness & duplicates ---------------------------------------
    for name, key in [("production", ["Year", "Country"]),
                      ("consumption", ["Year", "Country"]),
                      ("trade", ["Year", "Trade_Role", "Country"]),
                      ("prices", ["Year"])]:
        df = d[name]
        nulls = int(df.isna().sum().sum())
        dups = int(df.duplicated(key).sum())
        add(name, "No missing values", "PASS" if nulls == 0 else "FAIL", f"{nulls} missing cells")
        add(name, "No duplicate keys", "PASS" if dups == 0 else "FAIL", f"{dups} duplicate rows on {key}")

    # --- year coverage per country ---------------------------------------
    for name in ["production", "consumption"]:
        df = d[name]
        expected = set(range(BASE_YEAR, int(df["Year"].max()) + 1))
        bad = [c for c, g in df.groupby("Country") if set(g["Year"]) != expected]
        add(name, f"Every country has contiguous years {min(expected)}-{max(expected)}",
            "PASS" if not bad else "FAIL", "incomplete: " + ", ".join(bad) if bad else "all 5 countries complete")

    same = set(d["production"]["Country"]) == set(d["consumption"]["Country"])
    add("production/consumption", "Same country set in both files", "PASS" if same else "FAIL")

    # --- positive values --------------------------------------------------
    for name, col in [("production", "Coal_Production_Mt"), ("consumption", "Coal_Consumption_EJ"),
                      ("trade", "Coal_Trade_EJ")]:
        neg = int((d[name][col] <= 0).sum())
        add(name, "All values > 0", "PASS" if neg == 0 else "FAIL", f"{neg} non-positive values")

    # --- outlier YoY moves -------------------------------------------------
    for name, col in [("production", "Coal_Production_Mt"), ("consumption", "Coal_Consumption_EJ")]:
        df = d[name].sort_values(["Country", "Year"]).copy()
        df["yoy"] = df.groupby("Country")[col].pct_change() * 100
        big = df[df["yoy"].abs() > OUTLIER_YOY_PCT]
        if big.empty:
            add(name, f"No YoY move above {OUTLIER_YOY_PCT}%", "PASS")
        else:
            txt = "; ".join(f"{r.Country} {int(r.Year)} ({r.yoy:+.1f}%)" for r in big.itertuples())
            add(name, f"YoY move above {OUTLIER_YOY_PCT}% needs source check", "WARN",
                f"{txt}. Verify against the Energy Institute workbook (possible series revision).")

    low = d["production"][d["production"]["Coal_Production_Mt"] < LOW_BASE_MT]["Country"].unique()
    if len(low):
        add("production", f"Production below {LOW_BASE_MT} Mt (low base)", "WARN",
            f"{', '.join(low)}: YoY % swings on tiny absolute changes; interpret CAGR with care.")

    # --- trade internal consistency ---------------------------------------
    t = d["trade"].copy()
    t["implied_world_ej"] = t["Coal_Trade_EJ"] / t["Share_of_World_Trade_pct"] * 100
    for yr, g in t.groupby("Year"):
        spread = (g["implied_world_ej"].max() - g["implied_world_ej"].min()) / g["implied_world_ej"].mean()
        add("trade", f"{yr}: EJ / share implies one consistent world-trade total",
            "PASS" if spread <= SHARE_SPREAD_TOL else "WARN",
            f"implied world trade {g['implied_world_ej'].mean():.2f} EJ, spread {spread:.1%}")
    over = t.groupby(["Year", "Trade_Role"])["Share_of_World_Trade_pct"].sum()
    add("trade", "Share of world trade per role does not exceed 100%",
        "PASS" if (over <= 100).all() else "FAIL")

    pairs = {y: set(zip(g["Trade_Role"], g["Country"])) for y, g in t.groupby("Year")}
    years = sorted(pairs)
    missing = sorted(pairs[years[0]] - pairs[years[-1]])
    if missing:
        add("trade", f"Same exporter/importer list in {years[0]} and {years[-1]}", "WARN",
            "Missing in " + str(years[-1]) + ": " + ", ".join(f"{c} ({r})" for r, c in missing)
            + ". Year-on-year change and concentration are computed only on the comparable set.")
    else:
        add("trade", "Same exporter/importer list in both years", "PASS")

    # --- prices -------------------------------------------------------------
    p, pdet = d["prices"], d["price_detail"]
    add("prices", f"Annual price history {int(p['Year'].min())}-{int(p['Year'].max())} vs market data "
        f"{BASE_YEAR}-{int(d['production']['Year'].max())}", "WARN",
        "Price history is shorter than production/consumption history. Extend with the World Bank Pink Sheet "
        "annual series (see README, 'Extending the price history').")
    q25 = pdet[pdet["Period"].str.match(r"^2025-Q[1-4]$")]["Price_USD_per_mt"]
    ann25 = float(p.loc[p["Year"] == 2025, "Australia_Thermal_Coal_Price_USD_per_mt"].iloc[0])
    if len(q25) == 4:
        diff = abs(q25.mean() - ann25)
        add("prices", "2025 annual price equals mean of 2025 quarters", "PASS" if diff < 0.5 else "WARN",
            f"quarterly mean {q25.mean():.1f} vs annual {ann25:.1f}")
    add("price_detail", "Mixed granularity in 'Period' (quarters and months)", "INFO",
        "Split into Period_Type (Quarter/Month) in price_detail_clean.csv; do not average across types.")

    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# 3. METRICS
# --------------------------------------------------------------------------
def cagr(start, end, years):
    return (end / start) ** (1 / years) - 1


def market_metrics(d):
    m = (d["production"].merge(d["consumption"], on=["Year", "Country"], how="inner", validate="one_to_one")
         .sort_values(["Country", "Year"]).reset_index(drop=True))
    g = m.groupby("Country")
    m["Production_YoY_pct"] = g["Coal_Production_Mt"].pct_change() * 100
    m["Consumption_YoY_pct"] = g["Coal_Consumption_EJ"].pct_change() * 100
    m["Production_Index_2014"] = m["Coal_Production_Mt"] / g["Coal_Production_Mt"].transform("first") * 100
    m["Consumption_Index_2014"] = m["Coal_Consumption_EJ"] / g["Coal_Consumption_EJ"].transform("first") * 100
    m["Production_Share_of_Selected_pct"] = m["Coal_Production_Mt"] / m.groupby("Year")["Coal_Production_Mt"].transform("sum") * 100
    m["Consumption_Share_of_Selected_pct"] = m["Coal_Consumption_EJ"] / m.groupby("Year")["Coal_Consumption_EJ"].transform("sum") * 100
    return m


def country_summary(m):
    last = int(m["Year"].max())
    rows = []
    for c, g in m.groupby("Country"):
        g = g.set_index("Year")
        p0, p5, p1 = g.loc[BASE_YEAR, "Coal_Production_Mt"], g.loc[RECENT_YEAR, "Coal_Production_Mt"], g.loc[last, "Coal_Production_Mt"]
        c0, c5, c1 = g.loc[BASE_YEAR, "Coal_Consumption_EJ"], g.loc[RECENT_YEAR, "Coal_Consumption_EJ"], g.loc[last, "Coal_Consumption_EJ"]
        rows.append({
            "Country": c,
            f"Production_{BASE_YEAR}_Mt": p0, f"Production_{last}_Mt": p1,
            "Production_CAGR_10y_pct": cagr(p0, p1, last - BASE_YEAR) * 100,
            "Production_CAGR_5y_pct": cagr(p5, p1, last - RECENT_YEAR) * 100,
            f"Consumption_{BASE_YEAR}_EJ": c0, f"Consumption_{last}_EJ": c1,
            "Consumption_CAGR_10y_pct": cagr(c0, c1, last - BASE_YEAR) * 100,
            "Consumption_CAGR_5y_pct": cagr(c5, c1, last - RECENT_YEAR) * 100,
            f"Production_Share_{last}_pct": g.loc[last, "Production_Share_of_Selected_pct"],
            f"Consumption_Share_{last}_pct": g.loc[last, "Consumption_Share_of_Selected_pct"],
        })
    s = pd.DataFrame(rows)
    s["Growth_Gap_pp"] = s["Production_CAGR_10y_pct"] - s["Consumption_CAGR_10y_pct"]
    s[f"Production_Rank_{last}"] = s[f"Production_{last}_Mt"].rank(ascending=False).astype(int)
    s[f"Consumption_Rank_{last}"] = s[f"Consumption_{last}_EJ"].rank(ascending=False).astype(int)
    return s.sort_values(f"Production_{last}_Mt", ascending=False).reset_index(drop=True)


def trade_metrics(d, m):
    t = d["trade"].copy()
    t["Implied_World_Trade_EJ"] = t["Coal_Trade_EJ"] / t["Share_of_World_Trade_pct"] * 100
    t["Rank_in_Role"] = t.groupby(["Year", "Trade_Role"])["Coal_Trade_EJ"].rank(ascending=False).astype(int)
    t = t.sort_values(["Trade_Role", "Country", "Year"])
    t["YoY_pct"] = t.groupby(["Trade_Role", "Country"])["Coal_Trade_EJ"].pct_change() * 100
    t["Share_Change_pp"] = t.groupby(["Trade_Role", "Country"])["Share_of_World_Trade_pct"].diff()
    # Trade relative to domestic consumption (EJ / EJ, unit-consistent).
    cons = d["consumption"].rename(columns={"Coal_Consumption_EJ": "Domestic_Consumption_EJ"})
    t = t.merge(cons, on=["Year", "Country"], how="left")
    t["Trade_to_Consumption_ratio"] = t["Coal_Trade_EJ"] / t["Domestic_Consumption_EJ"]
    return t.sort_values(["Year", "Trade_Role", "Rank_in_Role"]).reset_index(drop=True)


def concentration(d):
    t = d["trade"]
    both = set.intersection(*[set(zip(g["Trade_Role"], g["Country"])) for _, g in t.groupby("Year")])
    rows = []
    for (yr, role), g in t.groupby(["Year", "Trade_Role"]):
        comp = g[[(role, c) in both for c in g["Country"]]]
        rows.append({
            "Year": yr, "Trade_Role": role, "Countries_Listed": len(g),
            "Combined_Share_Listed_pct": g["Share_of_World_Trade_pct"].sum(),
            "Top1_Share_pct": g["Share_of_World_Trade_pct"].max(),
            "HHI_Listed_LowerBound": (g["Share_of_World_Trade_pct"] ** 2).sum(),
            "Comparable_Set": ", ".join(sorted(comp["Country"])),
            "Combined_Share_Comparable_pct": comp["Share_of_World_Trade_pct"].sum(),
        })
    return pd.DataFrame(rows)


def price_metrics(d):
    p = d["prices"].sort_values("Year").copy()
    col = "Australia_Thermal_Coal_Price_USD_per_mt"
    p["Price_YoY_pct"] = p[col].pct_change() * 100
    p["Price_Index_2021"] = p[col] / p[col].iloc[0] * 100
    peak = p[col].max()
    p["Pct_vs_Peak"] = (p[col] / peak - 1) * 100
    p["Is_Peak_Year"] = p[col] == peak
    detail = d["price_detail"].copy()
    detail["Period_Type"] = np.where(detail["Period"].str.contains("Q"), "Quarter", "Month")
    detail["Year"] = detail["Period"].str[:4].astype(int)
    return p, detail


# --------------------------------------------------------------------------
# 4. CHARTS
# --------------------------------------------------------------------------
def _style(ax, title, ylabel, xlabel=""):
    ax.set_title(title, fontsize=13, fontweight="bold", loc="left", pad=12)
    ax.set_ylabel(ylabel)
    if xlabel:
        ax.set_xlabel(xlabel)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25)


def draw_charts(m, s, t, conc, p, detail):
    OUT.mkdir(exist_ok=True)
    last = int(m["Year"].max())
    order = list(s["Country"])

    # Production index (Japan excluded: ~0.5 Mt, index is not meaningful)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for c in order:
        if c == "Japan":
            continue
        g = m[m["Country"] == c]
        ax.plot(g["Year"], g["Production_Index_2014"], lw=2.4, color=COLORS[c], label=c)
        ax.annotate(f"{g['Production_Index_2014'].iloc[-1]:.0f}", (last, g["Production_Index_2014"].iloc[-1]),
                    xytext=(6, 0), textcoords="offset points", va="center", color=COLORS[c], fontsize=10)
    ax.axhline(100, color="black", lw=0.8, ls="--", alpha=0.5)
    _style(ax, "Coal production growth, indexed (2014 = 100)", "Index (2014 = 100)")
    ax.set_xlim(BASE_YEAR, last + 0.7)
    ax.legend(frameon=False, loc="upper left")
    fig.text(0.01, 0.01, "Source: Energy Institute Statistical Review 2025. Japan omitted (~0.5 Mt, negligible).",
             fontsize=8, color="gray")
    fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(OUT / "production_trend.png", dpi=160); plt.close(fig)

    # Consumption index
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for c in order:
        g = m[m["Country"] == c]
        ax.plot(g["Year"], g["Consumption_Index_2014"], lw=2.4, color=COLORS[c], label=c)
        ax.annotate(f"{g['Consumption_Index_2014'].iloc[-1]:.0f}", (last, g["Consumption_Index_2014"].iloc[-1]),
                    xytext=(6, 0), textcoords="offset points", va="center", color=COLORS[c], fontsize=10)
    ax.axhline(100, color="black", lw=0.8, ls="--", alpha=0.5)
    _style(ax, "Coal consumption growth, indexed (2014 = 100)", "Index (2014 = 100)")
    ax.set_xlim(BASE_YEAR, last + 0.7)
    ax.legend(frameon=False, loc="upper left")
    fig.text(0.01, 0.01, "Source: Energy Institute Statistical Review 2025. Indonesia's 2023 jump (+59%) should be verified.",
             fontsize=8, color="gray")
    fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(OUT / "consumption_trend.png", dpi=160); plt.close(fig)

    # Growth comparison: production vs consumption CAGR
    fig, ax = plt.subplots(figsize=(10, 5.5))
    x = np.arange(len(order)); w = 0.38
    sp = s.set_index("Country")
    b1 = ax.bar(x - w / 2, [sp.loc[c, "Production_CAGR_10y_pct"] for c in order], w, label="Production", color="#34495E")
    b2 = ax.bar(x + w / 2, [sp.loc[c, "Consumption_CAGR_10y_pct"] for c in order], w, label="Consumption", color="#E67E22")
    for bars in (b1, b2):
        for b in bars:
            h = b.get_height()
            ax.annotate(f"{h:.1f}%", (b.get_x() + b.get_width() / 2, h), xytext=(0, 4 if h >= 0 else -12),
                        textcoords="offset points", ha="center", fontsize=9)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels(order)
    _style(ax, f"Supply vs demand growth: 10-year CAGR ({BASE_YEAR}-{last})", "CAGR (%)")
    ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(OUT / "growth_comparison.png", dpi=160); plt.close(fig)

    # Trade 2023 vs 2024
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))
    for ax, role in zip(axes, ["Exporter", "Importer"]):
        g = t[t["Trade_Role"] == role]
        names = list(g.sort_values("Coal_Trade_EJ", ascending=False)["Country"].drop_duplicates())
        yrs = sorted(g["Year"].unique()); w = 0.38
        for i, yr in enumerate(yrs):
            vals = [g[(g["Country"] == c) & (g["Year"] == yr)]["Coal_Trade_EJ"].sum() for c in names]
            present = [not g[(g["Country"] == c) & (g["Year"] == yr)].empty for c in names]
            xs = np.arange(len(names)) + (i - 0.5) * w
            bars = ax.bar(xs, vals, w, label=str(yr), color=["#95A5A6", "#2C3E50"][i])
            for xb, v, ok in zip(xs, vals, present):
                ax.annotate(f"{v:.1f}" if ok else "n/a", (xb, v), xytext=(0, 3), textcoords="offset points",
                            ha="center", fontsize=8)
        ax.set_xticks(np.arange(len(names))); ax.set_xticklabels([n.replace("Russian Federation", "Russia") for n in names])
        _style(ax, f"Top {role.lower()}s (selected)", "Trade volume (EJ)")
        ax.legend(frameon=False)
    fig.text(0.01, 0.01, "Source: Energy Institute Statistical Review 2025. Russia is absent from the 2024 export data supplied.",
             fontsize=8, color="gray")
    fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(OUT / "trade_2023_vs_2024.png", dpi=160); plt.close(fig)

    # Trade vs domestic consumption (2024)
    g = t[(t["Year"] == last) & t["Trade_to_Consumption_ratio"].notna()].sort_values("Trade_to_Consumption_ratio")
    fig, ax = plt.subplots(figsize=(10, 4.8))
    cols = ["#2980B9" if r == "Exporter" else "#C0392B" for r in g["Trade_Role"]]
    ax.barh(g["Country"] + " (" + g["Trade_Role"].str.lower() + "s)", g["Trade_to_Consumption_ratio"], color=cols)
    for i, v in enumerate(g["Trade_to_Consumption_ratio"]):
        ax.annotate(f"{v:.2f}x", (v, i), xytext=(5, 0), textcoords="offset points", va="center", fontsize=10)
    ax.axvline(1, color="black", lw=0.8, ls="--")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title(f"Trade volume relative to domestic coal consumption, {last} (EJ / EJ)", fontsize=13,
                 fontweight="bold", loc="left", pad=12)
    ax.set_xlabel("Ratio (1.0x = trade equals domestic consumption)")
    fig.tight_layout(); fig.savefig(OUT / "trade_vs_consumption.png", dpi=160); plt.close(fig)

    # Price trend
    col = "Australia_Thermal_Coal_Price_USD_per_mt"
    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.plot(p["Year"], p[col], marker="o", lw=2.6, color="#2C3E50")
    for r in p.itertuples():
        ax.annotate(f"${getattr(r, col):.0f}", (r.Year, getattr(r, col)), xytext=(0, 9), textcoords="offset points",
                    ha="center", fontsize=10)
    pk = p.loc[p["Is_Peak_Year"]].iloc[0]
    ax.annotate(f"{int(pk.Year)} peak", (pk.Year, pk[col]), xytext=(25, -4), textcoords="offset points",
                color="#C0392B", fontsize=10, fontweight="bold")
    ax.set_ylim(0, p[col].max() * 1.18)
    ax.set_xticks(p["Year"])
    _style(ax, "Australian thermal coal benchmark price (annual average)", "USD per tonne")
    fig.text(0.01, 0.01, "Source: World Bank Commodity Price Data (Pink Sheet).", fontsize=8, color="gray")
    fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(OUT / "price_trend.png", dpi=160); plt.close(fig)


# --------------------------------------------------------------------------
# 5. FINDINGS (auto-generated so numbers always match the data)
# --------------------------------------------------------------------------
def write_findings(m, s, t, conc, p):
    last = int(m["Year"].max())
    sp = s.set_index("Country")
    col = "Australia_Thermal_Coal_Price_USD_per_mt"
    pk = p.loc[p["Is_Peak_Year"]].iloc[0]
    lp = p.iloc[-1]
    L = []
    top = s.iloc[0]
    L.append(f"- **Scale:** China produced {top[f'Production_{last}_Mt']:,.0f} Mt in {last} "
             f"({top[f'Production_Share_{last}_pct']:.0f}% of the five selected markets) and consumed "
             f"{top[f'Consumption_{last}_EJ']:.1f} EJ ({top[f'Consumption_Share_{last}_pct']:.0f}% of selected consumption).")
    i = sp.loc["India"]
    L.append(f"- **India:** production grew {i['Production_CAGR_10y_pct']:.1f}% a year and consumption "
             f"{i['Consumption_CAGR_10y_pct']:.1f}% a year over {BASE_YEAR}-{last}; consumption rose "
             f"{m[(m.Country == 'India') & (m.Year == last)]['Consumption_YoY_pct'].iloc[0]:.1f}% in {last} alone.")
    n = sp.loc["Indonesia"]
    big = m[m["Consumption_YoY_pct"].abs() > OUTLIER_YOY_PCT]
    flag = "".join(f"; includes a {r.Consumption_YoY_pct:+.0f}% jump in {int(r.Year)} that needs source verification"
                   for r in big[big.Country == "Indonesia"].itertuples())
    L.append(f"- **Indonesia:** production CAGR {n['Production_CAGR_10y_pct']:.1f}%, consumption CAGR "
             f"{n['Consumption_CAGR_10y_pct']:.1f}%{flag}.")
    tl = t[t["Year"] == last]
    ex = tl[tl["Trade_Role"] == "Exporter"].sort_values("Coal_Trade_EJ", ascending=False)
    L.append(f"- **Export dependence:** {ex.iloc[0]['Country']} exported {ex.iloc[0]['Coal_Trade_EJ']:.2f} EJ in {last} "
             f"({ex.iloc[0]['Trade_to_Consumption_ratio']:.1f}x its domestic consumption); "
             f"{ex.iloc[1]['Country']} exported {ex.iloc[1]['Coal_Trade_EJ']:.2f} EJ "
             f"({ex.iloc[1]['Trade_to_Consumption_ratio']:.1f}x its domestic consumption).")
    im = tl[tl["Trade_Role"] == "Importer"].set_index("Country")
    L.append(f"- **Import dependence ({last}, imports / domestic consumption):** Japan {im.loc['Japan', 'Trade_to_Consumption_ratio']:.0%}, "
             f"India {im.loc['India', 'Trade_to_Consumption_ratio']:.0%}, China {im.loc['China', 'Trade_to_Consumption_ratio']:.0%}.")
    ch = t[(t.Country == 'China') & (t.Trade_Role == 'Importer')].set_index("Year")
    L.append(f"- **China's import pull:** imports rose {ch.loc[last, 'YoY_pct']:.1f}% to {ch.loc[last, 'Coal_Trade_EJ']:.2f} EJ and its share of "
             f"world trade moved {ch.loc[last, 'Share_Change_pp']:+.1f} pp to {ch.loc[last, 'Share_of_World_Trade_pct']:.1f}%.")
    c = conc[conc["Year"] == last].set_index("Trade_Role")
    cp = conc[conc["Year"] == last - 1].set_index("Trade_Role")
    L.append(f"- **Concentration:** the two exporters present in both years ({c.loc['Exporter', 'Comparable_Set']}) supplied "
             f"{c.loc['Exporter', 'Combined_Share_Comparable_pct']:.1f}% of world trade in {last} "
             f"vs {cp.loc['Exporter', 'Combined_Share_Comparable_pct']:.1f}% in {last - 1}; the four listed importers took "
             f"{c.loc['Importer', 'Combined_Share_Listed_pct']:.1f}% (vs {cp.loc['Importer', 'Combined_Share_Listed_pct']:.1f}%).")
    L.append(f"- **Price:** Australian thermal coal averaged ${pk[col]:.0f}/t in {int(pk.Year)} (peak), "
             f"${lp[col]:.0f}/t in {int(lp.Year)} ({lp['Pct_vs_Peak']:.0f}% vs peak, "
             f"{(lp[col] / p.iloc[0][col] - 1) * 100:+.0f}% vs {int(p.iloc[0].Year)}).")
    jp = sp.loc["Japan"]
    au = sp.loc["Australia"]
    L.append(f"- **Contracting markets:** Australia (production {au['Production_CAGR_10y_pct']:.1f}%, consumption {au['Consumption_CAGR_10y_pct']:.1f}% CAGR) "
             f"and Japan (consumption {jp['Consumption_CAGR_10y_pct']:.1f}% CAGR) are shrinking domestically.")
    text = ("# Key findings (auto-generated by `python/market_analysis.py`)\n\n"
            "Historical observations from the data in this repository. They are not forecasts or investment advice.\n\n"
            + "\n".join(L) + "\n")
    (OUT / "key_findings.md").write_text(text, encoding="utf-8")
    return text


# --------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------
def main():
    PROC.mkdir(parents=True, exist_ok=True)
    d = load_raw()

    report = validate(d)
    report.to_csv(PROC / "data_quality_report.csv", index=False)
    print("DATA QUALITY REPORT")
    print(report.to_string(index=False, max_colwidth=90))
    if (report["Status"] == "FAIL").any():
        print("\nValidation FAILED - fix the raw data before using the outputs.")
        sys.exit(1)

    m = market_metrics(d)
    s = country_summary(m)
    t = trade_metrics(d, m)
    conc = concentration(d)
    p, detail = price_metrics(d)

    m.round(2).to_csv(PROC / "country_market_metrics.csv", index=False)
    s.round(2).to_csv(PROC / "country_summary.csv", index=False)
    t.round(3).to_csv(PROC / "trade_metrics.csv", index=False)
    conc.round(2).to_csv(PROC / "trade_concentration.csv", index=False)
    p.round(2).to_csv(PROC / "price_metrics.csv", index=False)
    detail.to_csv(PROC / "price_detail_clean.csv", index=False)

    draw_charts(m, s, t, conc, p, detail)
    findings = write_findings(m, s, t, conc, p)

    print("\nCOUNTRY SUMMARY"); print(s.round(2).T.to_string(header=False))
    print("\nTRADE CONCENTRATION"); print(conc.round(1).to_string(index=False))
    print("\nPRICE METRICS"); print(p.round(1).to_string(index=False))
    print("\n" + findings)
    print(f"Processed files -> {PROC}\nCharts + findings -> {OUT}")


if __name__ == "__main__":
    main()
