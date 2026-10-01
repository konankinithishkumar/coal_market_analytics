"""
Build excel/coal_market_business_analysis.xlsx from the raw CSV files.

    python python/market_analysis.py      # first (writes data_quality_report.csv, key_findings.md)
    python python/build_excel.py

Every analytical number in the workbook is a live Excel formula (SUMIFS, COUNTIFS, INDEX/MATCH,
SUMPRODUCT, RANK, AVERAGEIFS) pointing at the Data_* sheets, so editing or extending the data
sheets recalculates everything. Only the raw data (blue font) and the narrative text are typed values.
"""
from pathlib import Path
import re

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.formatting.rule import CellIsRule, ColorScaleRule, DataBarRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed", ROOT / "outputs"
XLSX = ROOT / "excel" / "coal_market_business_analysis.xlsx"

FONT = "Arial"
F_BASE = Font(name=FONT, size=10)
F_BOLD = Font(name=FONT, size=10, bold=True)
F_INPUT = Font(name=FONT, size=10, color="0000FF")
F_HDR = Font(name=FONT, size=10, bold=True, color="FFFFFF")
F_TITLE = Font(name=FONT, size=16, bold=True, color="1F2D3D")
F_SUB = Font(name=FONT, size=9, italic=True, color="666666")
F_KPI = Font(name=FONT, size=18, bold=True, color="1F2D3D")
FILL_HDR = PatternFill("solid", fgColor="1F2D3D")
FILL_INPUT = PatternFill("solid", fgColor="FFF9C4")
FILL_BAND = PatternFill("solid", fgColor="F4F6F8")
FILL_KPI = PatternFill("solid", fgColor="EAF0F6")
THIN = Side(style="thin", color="D0D5DA")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

MT = "Data_Market!$C$2:$C$500"
CE = "Data_Market!$D$2:$D$500"
MY = "Data_Market!$A$2:$A$500"
MC = "Data_Market!$B$2:$B$500"
MK = "Data_Market!$E$2:$E$500"
TY, TR, TC, TE, TS, TW = (f"Data_Trade!${c}$2:${c}$200" for c in "ABCDEF")
PY, PP = "Data_Prices!$A$2:$A$200", "Data_Prices!$B$2:$B$200"
MTR = "'Market Trends'"
TRA = "'Trade Analysis'"
PRA = "'Price Analysis'"
EXE = "'Executive Summary'"


def style_range(ws, rng, font=None, fill=None, border=None, align=None, fmt=None):
    for row in ws[rng]:
        for c in row:
            if font: c.font = font
            if fill: c.fill = fill
            if border: c.border = border
            if align: c.alignment = align
            if fmt: c.number_format = fmt


def header(ws, row, labels, col=1, height=42):
    for i, text in enumerate(labels):
        c = ws.cell(row=row, column=col + i, value=text)
        c.font, c.fill, c.border = F_HDR, FILL_HDR, BORDER
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[row].height = height


def title(ws, text, sub=None):
    ws["A1"] = text
    ws["A1"].font = F_TITLE
    ws.row_dimensions[1].height = 26
    if sub:
        ws["A2"] = sub
        ws["A2"].font = F_SUB
    ws.sheet_view.showGridLines = False


def widths(ws, mapping):
    for col, w in mapping.items():
        ws.column_dimensions[col].width = w


def base_font(ws):
    for row in ws.iter_rows():
        for c in row:
            if c.font == Font() or (c.font.name != FONT):
                c.font = F_BASE


# --------------------------------------------------------------------------
def build():
    prod = pd.read_csv(RAW / "coal_production_ei_2014_2024.csv")
    cons = pd.read_csv(RAW / "coal_consumption_ei_2014_2024.csv")
    trade = pd.read_csv(RAW / "coal_trade_selected_2023_2024.csv")
    price = pd.read_csv(RAW / "coal_price_worldbank_2021_2025.csv")
    detail = pd.read_csv(RAW / "coal_price_detail_worldbank.csv")
    market = prod.merge(cons, on=["Year", "Country"]).sort_values(["Country", "Year"])
    report = pd.read_csv(PROC / "data_quality_report.csv").fillna("")
    findings = [re.sub(r"\*\*", "", l[2:]) for l in (OUT / "key_findings.md").read_text(encoding="utf-8").splitlines()
                if l.startswith("- ")]

    wb = Workbook()
    wb.remove(wb.active)
    names = ["Executive Summary", "Business Dashboard", "Market Trends", "Trade Analysis", "Price Analysis",
             "Data_Market", "Data_Trade", "Data_Prices", "Data Quality", "Notes"]
    S = {n: wb.create_sheet(n) for n in names}

    # ---------------------------------------------------------------- DATA SHEETS
    ws = S["Data_Market"]
    header(ws, 1, ["Year", "Country", "Production_Mt", "Consumption_EJ", "Key"], height=24)
    for i, r in enumerate(market.itertuples(index=False), start=2):
        ws.cell(i, 1, int(r.Year)); ws.cell(i, 2, r.Country)
        ws.cell(i, 3, float(r.Coal_Production_Mt)); ws.cell(i, 4, float(r.Coal_Consumption_EJ))
        ws.cell(i, 5, f'=B{i}&"|"&A{i}')
        for c in range(1, 5):
            ws.cell(i, c).font = F_INPUT
        ws.cell(i, 3).number_format = "#,##0.0"; ws.cell(i, 4).number_format = "0.00"
    n = len(market) + 1
    t = Table(displayName="tblMarket", ref=f"A1:E{n}"); t.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=False)
    ws.add_table(t); ws.freeze_panes = "A2"
    widths(ws, {"A": 8, "B": 14, "C": 16, "D": 17, "E": 20})
    ws["G1"] = "Source: Energy Institute Statistical Review of World Energy 2025 (data/raw/coal_production_*.csv, coal_consumption_*.csv)."
    ws["G2"] = "Production in million tonnes (Mt). Consumption in exajoules (EJ). Blue = typed source data. Column E is a helper key for INDEX/MATCH lookups."
    ws["G3"] = "PivotTable: click any cell in this table, then Insert > PivotTable."
    for a in ("G1", "G2", "G3"): ws[a].font = F_SUB

    ws = S["Data_Trade"]
    header(ws, 1, ["Year", "Trade_Role", "Country", "Trade_EJ", "Share_of_World_Trade_pct", "Implied_World_Trade_EJ"], height=36)
    for i, r in enumerate(trade.itertuples(index=False), start=2):
        ws.cell(i, 1, int(r.Year)); ws.cell(i, 2, r.Trade_Role); ws.cell(i, 3, r.Country)
        ws.cell(i, 4, float(r.Coal_Trade_EJ)); ws.cell(i, 5, float(r.Share_of_World_Trade_pct))
        ws.cell(i, 6, f'=IFERROR(D{i}/E{i}*100,"")')
        for c in range(1, 6): ws.cell(i, c).font = F_INPUT
        ws.cell(i, 4).number_format = "0.00"; ws.cell(i, 5).number_format = "0.0"; ws.cell(i, 6).number_format = "0.00"
    n = len(trade) + 1
    t = Table(displayName="tblTrade", ref=f"A1:F{n}"); t.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=False)
    ws.add_table(t); ws.freeze_panes = "A2"
    widths(ws, {"A": 8, "B": 12, "C": 20, "D": 12, "E": 18, "F": 18})
    ws["H1"] = "Source: Energy Institute Statistical Review 2025 (data/raw/coal_trade_selected_2023_2024.csv). Selected countries only, not the full world list."
    ws["H2"] = "Implied world trade = Trade_EJ / share x 100. It should be roughly the same for every row in a year (a consistency check)."
    for a in ("H1", "H2"): ws[a].font = F_SUB

    ws = S["Data_Prices"]
    header(ws, 1, ["Year", "Australia_Thermal_Coal_USD_per_mt"], height=36)
    for i, r in enumerate(price.itertuples(index=False), start=2):
        ws.cell(i, 1, int(r.Year)).font = F_INPUT
        c = ws.cell(i, 2, float(r[1])); c.font = F_INPUT; c.number_format = "0.0"
    header(ws, 1, ["Period", "Period_Type", "Price_USD_per_mt"], col=4, height=36)
    for i, r in enumerate(detail.itertuples(index=False), start=2):
        ws.cell(i, 4, r.Period).font = F_INPUT
        ws.cell(i, 5, f'=IF(ISNUMBER(SEARCH("Q",D{i})),"Quarter","Month")')
        c = ws.cell(i, 6, float(r.Price_USD_per_mt)); c.font = F_INPUT; c.number_format = "0.0"
    widths(ws, {"A": 8, "B": 22, "C": 3, "D": 11, "E": 13, "F": 17})
    ws["H1"] = "Source: World Bank Commodity Price Data (Pink Sheet), Australian thermal coal, USD per tonne."
    ws["H2"] = "To extend the history: append earlier years to columns A:B. The Price Analysis sheet reads the first year automatically."
    for a in ("H1", "H2"): ws[a].font = F_SUB
    ws.freeze_panes = "A2"

    # ---------------------------------------------------------------- MARKET TRENDS
    ws = S["Market Trends"]
    title(ws, "Market Trends: supply and demand", "Production in Mt, consumption in EJ. Units differ, so supply and demand are compared through growth rates and indices, never subtracted.")
    labels = [("Base year", 2014), ("Recent window start", 2019), ("Latest year", 2024), ("Growth threshold (CAGR)", 0.02)]
    for k, (lab, val) in enumerate(labels, start=3):
        ws.cell(k, 1, lab).font = F_BOLD
        c = ws.cell(k, 2, val); c.font = F_INPUT; c.fill = FILL_INPUT; c.border = BORDER
        c.number_format = "0.0%" if isinstance(val, float) else "0"
    ws["C3"] = "<- yellow cells are assumptions you can change"; ws["C3"].font = F_SUB
    hdr = ["Country", "Production base year (Mt)", "Production recent start (Mt)", "Production latest (Mt)",
           "Production CAGR (full period)", "Production CAGR (recent)", "Share of selected production",
           "Consumption base year (EJ)", "Consumption recent start (EJ)", "Consumption latest (EJ)",
           "Consumption CAGR (full period)", "Consumption CAGR (recent)", "Share of selected consumption",
           "Growth gap: production minus consumption CAGR (pp)", "Production rank", "Consumption rank",
           "Market signal", "Production YoY, latest year", "Consumption YoY, latest year"]
    header(ws, 8, hdr, height=62)
    countries = ["China", "India", "Indonesia", "Australia", "Japan"]
    for k, cty in enumerate(countries):
        r = 9 + k
        ws.cell(r, 1, cty).font = F_INPUT
        for col, rng, yr in [("B", MT, "$B$3"), ("C", MT, "$B$4"), ("D", MT, "$B$5"),
                             ("H", CE, "$B$3"), ("I", CE, "$B$4"), ("J", CE, "$B$5")]:
            ws[f"{col}{r}"] = f"=SUMIFS({rng},{MC},$A{r},{MY},{yr})"
        ws[f"E{r}"] = f'=IFERROR((D{r}/B{r})^(1/($B$5-$B$3))-1,"n/a")'
        ws[f"F{r}"] = f'=IFERROR((D{r}/C{r})^(1/($B$5-$B$4))-1,"n/a")'
        ws[f"G{r}"] = f"=D{r}/D$14"
        ws[f"K{r}"] = f'=IFERROR((J{r}/H{r})^(1/($B$5-$B$3))-1,"n/a")'
        ws[f"L{r}"] = f'=IFERROR((J{r}/I{r})^(1/($B$5-$B$4))-1,"n/a")'
        ws[f"M{r}"] = f"=J{r}/J$14"
        ws[f"N{r}"] = f'=IFERROR((E{r}-K{r})*100,"n/a")'
        ws[f"O{r}"] = f"=RANK(D{r},$D$9:$D$13)"
        ws[f"P{r}"] = f"=RANK(J{r},$J$9:$J$13)"
        ws[f"Q{r}"] = (f'=IF(AND(E{r}>$B$6,K{r}>$B$6),"Supply and demand growing",'
                       f'IF(AND(E{r}<0,K{r}<0),"Supply and demand contracting",'
                       f'IF(K{r}>$B$6,"Demand-led growth",IF(E{r}>$B$6,"Supply-led growth","Mixed / flat"))))')
        ws[f"R{r}"] = (f'=IFERROR(INDEX({MT},MATCH($A{r}&"|"&$B$5,{MK},0))/'
                       f'INDEX({MT},MATCH($A{r}&"|"&($B$5-1),{MK},0))-1,"n/a")')
        ws[f"S{r}"] = (f'=IFERROR(INDEX({CE},MATCH($A{r}&"|"&$B$5,{MK},0))/'
                       f'INDEX({CE},MATCH($A{r}&"|"&($B$5-1),{MK},0))-1,"n/a")')
    ws["A14"] = "Total (selected)"
    for col in "BCDHIJ": ws[f"{col}14"] = f"=SUM({col}9:{col}13)"
    ws["E14"] = '=IFERROR((D14/B14)^(1/($B$5-$B$3))-1,"n/a")'; ws["F14"] = '=IFERROR((D14/C14)^(1/($B$5-$B$4))-1,"n/a")'
    ws["K14"] = '=IFERROR((J14/H14)^(1/($B$5-$B$3))-1,"n/a")'; ws["L14"] = '=IFERROR((J14/I14)^(1/($B$5-$B$4))-1,"n/a")'
    ws["G14"] = "=SUM(G9:G13)"; ws["M14"] = "=SUM(M9:M13)"
    style_range(ws, "A9:S14", font=F_BASE, border=BORDER)
    style_range(ws, "A14:S14", font=F_BOLD, fill=FILL_BAND)
    for r in range(9, 14): ws.cell(r, 1).font = F_INPUT
    style_range(ws, "B9:D14", fmt="#,##0.0"); style_range(ws, "H9:J14", fmt="0.00")
    style_range(ws, "E9:G14", fmt="0.0%"); style_range(ws, "K9:M14", fmt="0.0%")
    style_range(ws, "N9:N14", fmt="0.0"); style_range(ws, "R9:S13", fmt="0.0%")
    style_range(ws, "O9:P13", fmt="0", align=Alignment(horizontal="center"))
    ws.conditional_formatting.add("E9:F13", ColorScaleRule(start_type="min", start_color="F8B4B4", mid_type="num", mid_value=0, mid_color="FFFFFF", end_type="max", end_color="A8D5BA"))
    ws.conditional_formatting.add("K9:L13", ColorScaleRule(start_type="min", start_color="F8B4B4", mid_type="num", mid_value=0, mid_color="FFFFFF", end_type="max", end_color="A8D5BA"))
    ws.conditional_formatting.add("G9:G13", DataBarRule(start_type="num", start_value=0, end_type="num", end_value=1, color="5B8DB8"))
    ws.conditional_formatting.add("M9:M13", DataBarRule(start_type="num", start_value=0, end_type="num", end_value=1, color="E39A4B"))
    ws.conditional_formatting.add("R9:S13", CellIsRule(operator="greaterThan", formula=["0.4"], font=Font(name=FONT, bold=True, color="C0392B")))
    ws["A15"] = ("Caution: Indonesia consumption jumped +59% in 2023 (see Data Quality) and Japan produces about 0.5 Mt, so their "
                 "CAGRs are sensitive to a single data point. Red YoY = move above 40%.")
    ws["A15"].font = F_SUB

    ws["A17"] = "Production index (base year = 100)"; ws["A17"].font = F_BOLD
    ws["H17"] = "Consumption index (base year = 100)"; ws["H17"].font = F_BOLD
    header(ws, 18, ["Year"] + [None] * 5, height=24)
    header(ws, 18, ["Year"] + [None] * 5, col=8, height=24)
    for k in range(5):
        ws.cell(18, 2 + k, f"=$A${9 + k}"); ws.cell(18, 9 + k, f"=$A${9 + k}")
    for k in range(11):
        r = 19 + k
        ws[f"A{r}"] = "=$B$3" if k == 0 else f"=A{r - 1}+1"
        ws[f"H{r}"] = f"=A{r}"
        for j in range(5):
            pc, cc = ws.cell(18, 2 + j).column_letter, ws.cell(18, 9 + j).column_letter
            ws[f"{pc}{r}"] = (f"=SUMIFS({MT},{MC},{pc}$18,{MY},$A{r})/SUMIFS({MT},{MC},{pc}$18,{MY},$B$3)*100")
            ws[f"{cc}{r}"] = (f"=SUMIFS({CE},{MC},{cc}$18,{MY},$H{r})/SUMIFS({CE},{MC},{cc}$18,{MY},$B$3)*100")
    style_range(ws, "A19:F29", font=F_BASE, border=BORDER, fmt="0.0")
    style_range(ws, "H19:M29", font=F_BASE, border=BORDER, fmt="0.0")
    style_range(ws, "A19:A29", fmt="0"); style_range(ws, "H19:H29", fmt="0")
    widths(ws, {"A": 22, "B": 13, "C": 13, "D": 13, "E": 14, "F": 13, "G": 14, "H": 13, "I": 13, "J": 13, "K": 14,
                "L": 13, "M": 14, "N": 18, "O": 11, "P": 12, "Q": 28, "R": 14, "S": 14})
    ws.freeze_panes = "B9"

    # ---------------------------------------------------------------- TRADE ANALYSIS
    ws = S["Trade Analysis"]
    title(ws, "Trade Analysis: exposure and concentration", "Selected exporters and importers only (not the full world list). Volumes in EJ so they can be compared with domestic consumption.")
    for k, (lab, val) in enumerate([("Prior year", 2023), ("Latest year", 2024)], start=3):
        ws.cell(k, 1, lab).font = F_BOLD
        c = ws.cell(k, 2, val); c.font = F_INPUT; c.fill = FILL_INPUT; c.border = BORDER
    header(ws, 7, ["Role", "Country", "Prior year volume (EJ)", "Latest volume (EJ)", "YoY change", "Prior share of world trade (%)",
                   "Latest share of world trade (%)", "Share change (pp)", "Reported in both years?",
                   "Domestic consumption, latest (EJ)", "Trade / domestic consumption (x)", "Read-across"], height=62)
    entries = [("Exporter", "Indonesia"), ("Exporter", "Australia"), ("Exporter", "Russian Federation"),
               ("Importer", "China"), ("Importer", "India"), ("Importer", "Japan"), ("Importer", "South Korea")]
    for k, (role, cty) in enumerate(entries):
        r = 8 + k
        ws.cell(r, 1, role).font = F_INPUT; ws.cell(r, 2, cty).font = F_INPUT
        for col, yr, val_rng in [("C", "$B$3", TE), ("D", "$B$4", TE), ("F", "$B$3", TS), ("G", "$B$4", TS)]:
            ws[f"{col}{r}"] = (f'=IF(COUNTIFS({TY},{yr},{TR},$A{r},{TC},$B{r})=0,"n/a",'
                               f'SUMIFS({val_rng},{TY},{yr},{TR},$A{r},{TC},$B{r}))')
        ws[f"E{r}"] = f'=IF(AND(ISNUMBER(C{r}),ISNUMBER(D{r})),D{r}/C{r}-1,"n/a")'
        ws[f"H{r}"] = f'=IF(AND(ISNUMBER(F{r}),ISNUMBER(G{r})),G{r}-F{r},"n/a")'
        ws[f"I{r}"] = f'=IF(AND(ISNUMBER(C{r}),ISNUMBER(D{r})),"Yes","No")'
        ws[f"J{r}"] = f'=IFERROR(INDEX({CE},MATCH($B{r}&"|"&$B$4,{MK},0)),"n/a")'
        ws[f"K{r}"] = f'=IF(AND(ISNUMBER(D{r}),ISNUMBER(J{r})),D{r}/J{r},"n/a")'
        ws[f"L{r}"] = (f'=IF(I{r}="No","Missing in one year: excluded from comparisons",'
                       f'IF(E{r}>0.05,"Volume up more than 5%",IF(E{r}<-0.02,"Volume down","Broadly stable")))')
    style_range(ws, "A8:L14", font=F_BASE, border=BORDER)
    for r in range(8, 15): ws.cell(r, 1).font = F_INPUT; ws.cell(r, 2).font = F_INPUT
    style_range(ws, "C8:D14", fmt="0.00"); style_range(ws, "E8:E14", fmt="0.0%"); style_range(ws, "F8:G14", fmt="0.0")
    style_range(ws, "H8:H14", fmt="+0.0;-0.0;0.0"); style_range(ws, "J8:J14", fmt="0.00"); style_range(ws, "K8:K14", fmt='0.00"x"')
    style_range(ws, "I8:I14", align=Alignment(horizontal="center"))
    ws.conditional_formatting.add("E8:E14", CellIsRule(operator="lessThan", formula=["0"], font=Font(name=FONT, color="C0392B")))
    ws.conditional_formatting.add("E8:E14", CellIsRule(operator="greaterThan", formula=["0"], font=Font(name=FONT, color="1E8449")))
    ws.conditional_formatting.add("K8:K14", DataBarRule(start_type="num", start_value=0, end_type="num", end_value=6, color="5B8DB8"))
    ws.conditional_formatting.add("I8:I14", CellIsRule(operator="equal", formula=['"No"'], fill=PatternFill("solid", bgColor="FCE4E4")))

    ws["A16"] = "Concentration of selected trade"; ws["A16"].font = F_BOLD
    header(ws, 17, ["Role", "Year", "Countries listed", "Combined share listed (%)", "Top single share (%)",
                    "HHI (listed only, lower bound)", "Share of countries reported in both years (%)"], height=50)
    rows = [("Exporter", "$B$3", "F"), ("Exporter", "$B$4", "G"), ("Importer", "$B$3", "F"), ("Importer", "$B$4", "G")]
    for k, (role, yr, scol) in enumerate(rows):
        r = 18 + k
        ws[f"A{r}"] = role; ws[f"A{r}"].font = F_INPUT
        ws[f"B{r}"] = f"={yr}"
        ws[f"C{r}"] = f"=COUNTIFS({TY},$B{r},{TR},$A{r})"
        ws[f"D{r}"] = f"=SUMIFS({TS},{TY},$B{r},{TR},$A{r})"
        ws[f"E{r}"] = f"=SUMPRODUCT(MAX(({TY}=$B{r})*({TR}=$A{r})*{TS}))"
        ws[f"F{r}"] = f"=SUMPRODUCT(({TY}=$B{r})*({TR}=$A{r})*{TS}^2)"
        ws[f"G{r}"] = f'=SUMIFS(${scol}$8:${scol}$14,$A$8:$A$14,$A{r},$I$8:$I$14,"Yes")'
    style_range(ws, "A18:G21", font=F_BASE, border=BORDER)
    for r in range(18, 22): ws.cell(r, 1).font = F_INPUT
    style_range(ws, "B18:C21", fmt="0"); style_range(ws, "D18:E21", fmt="0.0"); style_range(ws, "F18:F21", fmt="#,##0"); style_range(ws, "G18:G21", fmt="0.0")
    ws["A22"] = ("Like-for-like comparison uses the last column: it keeps only countries reported in both years. Listed-country totals "
                 "are not comparable across years because Russia is missing in 2024. HHI is a lower bound (unlisted countries add to it).")
    ws["A22"].font = F_SUB

    ws["A24"] = "Checks and counts"; ws["A24"].font = F_BOLD
    checks = [("Implied world trade, prior year (EJ)", f"=AVERAGEIFS({TW},{TY},$B$3)", "0.00"),
              ("Implied world trade, latest year (EJ)", f"=AVERAGEIFS({TW},{TY},$B$4)", "0.00"),
              ("Entries with higher volume than prior year", '=COUNTIFS($E$8:$E$14,">0")', "0"),
              ("Entries not reported in both years", '=COUNTIFS($I$8:$I$14,"No")', "0")]
    for k, (lab, f, fmt) in enumerate(checks):
        r = 25 + k
        ws[f"A{r}"] = lab; ws[f"D{r}"] = f; ws[f"D{r}"].number_format = fmt
        ws[f"A{r}"].font = F_BASE; ws[f"D{r}"].font = F_BASE; ws[f"D{r}"].border = BORDER
    widths(ws, {"A": 12, "B": 20, "C": 13, "D": 13, "E": 14, "F": 15, "G": 18, "H": 12, "I": 14, "J": 16, "K": 16, "L": 44})

    # ---------------------------------------------------------------- PRICE ANALYSIS
    ws = S["Price Analysis"]
    title(ws, "Price Analysis: Australian thermal coal benchmark", "USD per tonne, annual averages (World Bank Pink Sheet). Historical observations only, not a forecast.")
    header(ws, 6, ["Year", "Price (USD/t)", "YoY change", "Index (first year = 100)", "Vs peak year", "Flag"], height=40)
    for k in range(5):
        r = 7 + k
        ws[f"A{r}"] = f"=MIN({PY})" if k == 0 else f"=A{r - 1}+1"
        ws[f"B{r}"] = f"=INDEX({PP},MATCH($A{r},{PY},0))"
        ws[f"C{r}"] = '="n/a"' if k == 0 else f"=B{r}/B{r - 1}-1"
        ws[f"D{r}"] = f"=B{r}/$B$7*100"
        ws[f"E{r}"] = f"=B{r}/MAX($B$7:$B$11)-1"
        ws[f"F{r}"] = f'=IF(B{r}=MAX($B$7:$B$11),"Peak","")'
    style_range(ws, "A7:F11", font=F_BASE, border=BORDER)
    style_range(ws, "A7:A11", fmt="0"); style_range(ws, "B7:B11", fmt="0.0"); style_range(ws, "C7:C11", fmt="0.0%")
    style_range(ws, "D7:D11", fmt="0.0"); style_range(ws, "E7:E11", fmt="0.0%")
    ws.conditional_formatting.add("C8:C11", CellIsRule(operator="lessThan", formula=["0"], font=Font(name=FONT, color="C0392B")))
    ws.conditional_formatting.add("C8:C11", CellIsRule(operator="greaterThan", formula=["0"], font=Font(name=FONT, color="1E8449")))
    ws.conditional_formatting.add("B7:B11", DataBarRule(start_type="num", start_value=0, end_type="max", color="7F8C8D"))
    ws["A13"] = "Summary"; ws["A13"].font = F_BOLD
    summ = [("Peak price (USD/t)", "=MAX($B$7:$B$11)", "0.0"),
            ("Peak year", "=INDEX($A$7:$A$11,MATCH(MAX($B$7:$B$11),$B$7:$B$11,0))", "0"),
            ("Latest price (USD/t)", "=$B$11", "0.0"),
            ("Latest price vs peak", "=$B$11/MAX($B$7:$B$11)-1", "0.0%"),
            ("Latest price vs first year", "=$B$11/$B$7-1", "0.0%"),
            ("Years priced below the first-year level", '=COUNTIFS($B$7:$B$11,"<"&$B$7)', "0"),
            ("Average price over the period (USD/t)", "=AVERAGE($B$7:$B$11)", "0.0")]
    for k, (lab, f, fmt) in enumerate(summ):
        r = 14 + k
        ws[f"A{r}"] = lab; ws[f"B{r}"] = f; ws[f"B{r}"].number_format = fmt
        ws[f"A{r}"].font = F_BASE; ws[f"B{r}"].font = F_BASE; ws[f"B{r}"].border = BORDER
    ws["A22"] = "Reconciliation: annual vs quarterly"; ws["A22"].font = F_BOLD
    rec = [("Mean of 2025 quarterly prices", f'=AVERAGEIFS(Data_Prices!$F$2:$F$200,Data_Prices!$D$2:$D$200,"2025-Q*")', "0.0"),
           ("2025 annual price", f"=INDEX({PP},MATCH(2025,{PY},0))", "0.0"),
           ("Difference", "=B23-B24", "0.00"),
           ("Status", '=IF(ABS(B25)<0.5,"OK: annual matches quarters","Check source")', "@")]
    for k, (lab, f, fmt) in enumerate(rec):
        r = 23 + k
        ws[f"A{r}"] = lab; ws[f"B{r}"] = f; ws[f"B{r}"].number_format = fmt
        ws[f"A{r}"].font = F_BASE; ws[f"B{r}"].font = F_BASE; ws[f"B{r}"].border = BORDER
    ws["A28"] = ("Limitation: only 2021-2025 annual prices are loaded, while production/consumption cover 2014-2024. "
                 "Append earlier years to Data_Prices to extend every table here.")
    ws["A28"].font = F_SUB
    widths(ws, {"A": 40, "B": 26, "C": 13, "D": 16, "E": 13, "F": 10})

    # ---------------------------------------------------------------- EXECUTIVE SUMMARY
    ws = S["Executive Summary"]
    title(ws, "Coal Market & Supply Analytics: Executive Summary",
          "Selected markets: China, India, Indonesia, Australia, Japan. All KPI values below are live formulas.")
    header(ws, 4, ["Metric", "Value", "Basis"], height=24)
    kpis = [
        ("Latest year of market data", f"={MTR}!$B$5", "0", "Market Trends"),
        ("Largest producer", f"=INDEX({MTR}!$A$9:$A$13,MATCH(MAX({MTR}!$D$9:$D$13),{MTR}!$D$9:$D$13,0))", "@", "Highest production, latest year"),
        ("  production (Mt)", f"=MAX({MTR}!$D$9:$D$13)", "#,##0", "Million tonnes"),
        ("  share of selected-market production", f"=MAX({MTR}!$G$9:$G$13)", "0.0%", "Five selected countries only"),
        ("Fastest production growth", f"=INDEX({MTR}!$A$9:$A$13,MATCH(MAX({MTR}!$E$9:$E$13),{MTR}!$E$9:$E$13,0))", "@", "Full-period CAGR"),
        ("  production CAGR", f"=MAX({MTR}!$E$9:$E$13)", "0.0%", ""),
        ("Fastest consumption growth", f"=INDEX({MTR}!$A$9:$A$13,MATCH(MAX({MTR}!$K$9:$K$13),{MTR}!$K$9:$K$13,0))", "@", "Full-period CAGR (Indonesia affected by 2023 jump, see Data Quality)"),
        ("  consumption CAGR", f"=MAX({MTR}!$K$9:$K$13)", "0.0%", ""),
        ("Largest importer", f"=INDEX({TRA}!$B$11:$B$14,MATCH(MAX({TRA}!$D$11:$D$14),{TRA}!$D$11:$D$14,0))", "@", "Latest year, selected importers"),
        ("  imports (EJ)", f"=MAX({TRA}!$D$11:$D$14)", "0.00", ""),
        ("  share of world coal trade", f"=INDEX({TRA}!$G$11:$G$14,MATCH(MAX({TRA}!$D$11:$D$14),{TRA}!$D$11:$D$14,0))/100", "0.0%", ""),
        ("Largest exporter", f"=INDEX({TRA}!$B$8:$B$10,MATCH(MAX({TRA}!$D$8:$D$10),{TRA}!$D$8:$D$10,0))", "@", "Latest year, selected exporters"),
        ("  exports (EJ)", f"=MAX({TRA}!$D$8:$D$10)", "0.00", ""),
        ("  share of world coal trade", f"=INDEX({TRA}!$G$8:$G$10,MATCH(MAX({TRA}!$D$8:$D$10),{TRA}!$D$8:$D$10,0))/100", "0.0%", ""),
        ("Top two exporters, share of world trade (latest)", f"={TRA}!$G$19/100", "0.0%", "Countries reported in both years (like-for-like)"),
        ("Top two exporters, share of world trade (prior)", f"={TRA}!$G$18/100", "0.0%", "Same countries"),
        ("Benchmark price, latest year (USD/t)", f"={PRA}!$B$16", "0.0", "Australian thermal coal"),
        ("Benchmark price at peak (USD/t)", f"={PRA}!$B$14", "0.0", "Peak year in Price Analysis"),
        ("Latest price vs peak", f"={PRA}!$B$17", "0.0%", ""),
    ]
    for k, (lab, f, fmt, note) in enumerate(kpis):
        r = 5 + k
        ws[f"A{r}"] = lab; ws[f"B{r}"] = f; ws[f"C{r}"] = note
        ws[f"B{r}"].number_format = fmt; ws[f"B{r}"].alignment = Alignment(horizontal="right")
        ws[f"A{r}"].font = F_BOLD if not lab.startswith("  ") else F_BASE
        ws[f"B{r}"].font = F_BASE; ws[f"C{r}"].font = F_SUB
        for c in "ABC": ws[f"{c}{r}"].border = BORDER
    last_kpi = 4 + len(kpis)
    r0 = last_kpi + 2
    ws[f"A{r0}"] = "Key findings (narrative generated from the data when the workbook was built)"; ws[f"A{r0}"].font = F_BOLD
    for k, text in enumerate(findings):
        c = ws.cell(r0 + 1 + k, 1, text)
        ws.merge_cells(start_row=r0 + 1 + k, start_column=1, end_row=r0 + 1 + k, end_column=3)
        c.alignment = Alignment(wrap_text=True, vertical="top"); c.font = F_BASE
        ws.row_dimensions[r0 + 1 + k].height = 42
    r1 = r0 + len(findings) + 2
    ws[f"A{r1}"] = "Where each business question is answered"; ws[f"A{r1}"].font = F_BOLD
    qa = [("Which markets show sustained production and consumption growth?", "Market Trends"),
          ("Which importers represent the largest demand pools?", "Trade Analysis"),
          ("How concentrated is selected international coal trade?", "Trade Analysis (concentration table)"),
          ("How has benchmark thermal-coal pricing changed since the 2022 spike?", "Price Analysis"),
          ("Where do supply growth and demand growth diverge?", "Market Trends (growth gap and signal columns)"),
          ("Which data points should be verified before relying on conclusions?", "Data Quality")]
    for k, (q, where) in enumerate(qa):
        r = r1 + 1 + k
        ws[f"A{r}"] = q; ws[f"B{r}"] = where
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=3)
        for c in "AB": ws[f"{c}{r}"].font = F_BASE; ws[f"{c}{r}"].border = BORDER
    ws[f"A{r1 + len(qa) + 2}"] = "These are historical observations from public data, not forecasts or investment recommendations."
    ws[f"A{r1 + len(qa) + 2}"].font = F_SUB
    widths(ws, {"A": 62, "B": 24, "C": 62})

    # ---------------------------------------------------------------- DASHBOARD
    ws = S["Business Dashboard"]
    title(ws, "Business Dashboard", "All tiles and charts read from the analysis sheets and update when the data sheets change.")
    tiles = [("A4", "Largest producer", f"={EXE}!$B$6", "@"), ("D4", "Largest producer share", f"={EXE}!$B$8", "0%"),
             ("G4", "Largest importer", f"={EXE}!$B$13", "@"), ("J4", "Latest price vs peak", f"={EXE}!$B$23", "0%")]
    for cell, lab, f, fmt in tiles:
        col = ws[cell].column; row = ws[cell].row
        ws.cell(row, col, lab).font = F_SUB
        c = ws.cell(row + 1, col, f); c.font = F_KPI; c.number_format = fmt; c.alignment = Alignment(horizontal="left")
        for rr in (row, row + 1):
            for cc in range(col, col + 3): ws.cell(rr, cc).fill = FILL_KPI
        ws.row_dimensions[row + 1].height = 30
    mt = S["Market Trends"]; ta = S["Trade Analysis"]; pa = S["Price Analysis"]

    def line(title_text, ytitle, data_ref, cats_ref, anchor):
        ch = LineChart(); ch.title = title_text; ch.height = 8.2; ch.width = 14.0
        ch.y_axis.title = ytitle; ch.add_data(data_ref, titles_from_data=True); ch.set_categories(cats_ref)
        ch.x_axis.delete = False; ch.y_axis.delete = False; ch.legend.position = "b"
        for s in ch.series: s.smooth = False; s.graphicalProperties.line.width = 22000
        ws.add_chart(ch, anchor)

    line("Production index (base year = 100, Japan omitted)", "Index", Reference(mt, min_col=2, max_col=5, min_row=18, max_row=29),
         Reference(mt, min_col=1, min_row=19, max_row=29), "A8")
    line("Consumption index (base year = 100)", "Index", Reference(mt, min_col=9, max_col=13, min_row=18, max_row=29),
         Reference(mt, min_col=8, min_row=19, max_row=29), "H8")
    bc = BarChart(); bc.type = "col"; bc.title = "Selected coal trade, prior vs latest year (EJ)"; bc.height = 8.2; bc.width = 14.0
    bc.add_data(Reference(ta, min_col=3, max_col=4, min_row=7, max_row=14), titles_from_data=True)
    bc.set_categories(Reference(ta, min_col=2, min_row=8, max_row=14)); bc.y_axis.title = "EJ"
    bc.x_axis.delete = False; bc.y_axis.delete = False; bc.legend.position = "b"
    ws.add_chart(bc, "A25")
    line("Australian thermal coal price (USD/t)", "USD per tonne", Reference(pa, min_col=2, min_row=6, max_row=11),
         Reference(pa, min_col=1, min_row=7, max_row=11), "H25")
    ws["A41"] = "Note: Russia has no 2024 export figure in the supplied data, so its 2024 bar is empty. Not a zero."
    ws["A41"].font = F_SUB
    widths(ws, {c: 10.5 for c in "ABCDEFGHIJKLMNOP"})

    # ---------------------------------------------------------------- DATA QUALITY
    ws = S["Data Quality"]
    title(ws, "Data Quality Report", "Produced by python/market_analysis.py. PASS = check succeeded, WARN = review before relying on the figure, INFO = context.")
    header(ws, 4, ["Dataset", "Check", "Status", "Detail"], height=24)
    for k, r in enumerate(report.itertuples(index=False)):
        for j, v in enumerate([r.Dataset, r.Check, r.Status, r.Detail]):
            c = ws.cell(5 + k, 1 + j, v); c.font = F_BASE; c.border = BORDER
            c.alignment = Alignment(wrap_text=True, vertical="top")
    end = 4 + len(report)
    ws.conditional_formatting.add(f"C5:C{end}", CellIsRule(operator="equal", formula=['"PASS"'], fill=PatternFill("solid", bgColor="D5F0DD")))
    ws.conditional_formatting.add(f"C5:C{end}", CellIsRule(operator="equal", formula=['"WARN"'], fill=PatternFill("solid", bgColor="FFE9B5")))
    ws.conditional_formatting.add(f"C5:C{end}", CellIsRule(operator="equal", formula=['"FAIL"'], fill=PatternFill("solid", bgColor="F8B4B4")))
    widths(ws, {"A": 22, "B": 58, "C": 9, "D": 90}); ws.freeze_panes = "A5"

    # ---------------------------------------------------------------- NOTES
    ws = S["Notes"]
    title(ws, "Notes, units and conventions")
    notes = [
        ("Purpose", "Business-review workbook for coal supply, demand, trade exposure and benchmark price tracking."),
        ("Sources", "Energy Institute Statistical Review of World Energy 2025 (production, consumption, trade). World Bank Pink Sheet (Australian thermal coal price)."),
        ("Units", "Production: million tonnes (Mt). Consumption and trade: exajoules (EJ). Price: USD per tonne. Production and consumption are NOT subtracted because the units differ."),
        ("Colour code", "Blue font = typed source data or label. Black = formula. Yellow fill = assumption you may change."),
        ("Formulas used", "SUMIFS, COUNTIFS, AVERAGEIFS, INDEX/MATCH (lookups), SUMPRODUCT, RANK, IF/IFERROR. INDEX/MATCH is used instead of XLOOKUP so the file also calculates in older Excel and LibreOffice."),
        ("PivotTable", "Not embedded (a file generator cannot create a native PivotTable). Data_Market is an Excel Table: click inside it, Insert > PivotTable."),
        ("Growth maths", "CAGR = (end / start) ^ (1 / years) - 1. Index = value / base-year value x 100."),
        ("Import / export ratio", "Trade volume divided by domestic consumption, both in EJ. For importers this approximates import reliance; for exporters it shows how large exports are relative to home use."),
        ("Concentration", "HHI = sum of squared shares (0-10,000 scale) over the countries LISTED. Unlisted countries would add to it, so it is a lower bound."),
        ("Limitations", "Selected countries only; historical statistics are revised by the source; prices cover 2021-2025 only; no forecasts."),
        ("Refresh", "Run python/market_analysis.py then python/build_excel.py to regenerate this workbook from data/raw."),
    ]
    for k, (a, b) in enumerate(notes):
        ws.cell(3 + k, 1, a).font = F_BOLD
        c = ws.cell(3 + k, 2, b); c.font = F_BASE; c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[3 + k].height = 32
    widths(ws, {"A": 22, "B": 120})

    from openpyxl.worksheet.properties import PageSetupProperties
    for name, sh in S.items():
        base_font(sh)
        sh.page_setup.orientation = "landscape"
        sh.page_setup.fitToWidth = 1
        sh.page_setup.fitToHeight = 0
        sh.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    XLSX.parent.mkdir(exist_ok=True)
    wb.save(XLSX)
    print("saved", XLSX)


if __name__ == "__main__":
    build()
