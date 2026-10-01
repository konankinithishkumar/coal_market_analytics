# SQL query results (verified in SQLite)

## Q1: Which selected markets produce the most coal, and what share of the five-market total do they hold?

```
  country  production_mt  share_of_selected_pct  production_rank
    China         4780.0                  66.72                1
    India         1085.1                  15.15                2
Indonesia          836.1                  11.67                3
Australia          462.9                   6.46                4
    Japan            0.5                   0.01                5
```

## Q2: Which selected markets consume the most coal (EJ), and what is their share?

```
  country  consumption_ej  share_of_selected_pct  consumption_rank
    China           92.16                  73.20                 1
    India           22.97                  18.24                 2
Indonesia            4.72                   3.75                 3
    Japan            4.53                   3.60                 4
Australia            1.52                   1.21                 5
```

## Q3: Long-term growth (CAGR over the full period) for production and consumption, with the growth gap

```
  country  production_start_mt  production_end_mt  production_cagr_pct  consumption_start_ej  consumption_end_ej  consumption_cagr_pct  growth_gap_pp
Indonesia                458.1              836.1                 6.20                  1.59                4.72                 11.49          -5.29
    India                646.2             1085.1                 5.32                 14.44               22.97                  4.75           0.57
    China               3873.9             4780.0                 2.12                 82.45               92.16                  1.12           1.00
Australia                505.3              462.9                -0.87                  1.89                1.52                 -2.16           1.28
    Japan                  1.3                0.5                -9.11                  5.07                4.53                 -1.12          -7.99
```

## Q4: Year-over-year growth in production and consumption (window function LAG)

```
 year   country  production_mt  consumption_ej  production_yoy_pct  consumption_yoy_pct
 2014 Australia          505.3            1.89                 NaN                  NaN
 2015 Australia          503.7            1.88               -0.32                -0.53
 2016 Australia          502.1            1.95               -0.32                 3.72
 2017 Australia          487.2            1.94               -2.97                -0.51
 2018 Australia          502.0            1.88                3.04                -3.09
 2019 Australia          505.4            1.83                0.68                -2.66
 2020 Australia          467.9            1.75               -7.42                -4.37
 2021 Australia          478.8            1.69                2.33                -3.43
 2022 Australia          458.5            1.63               -4.24                -3.55
 2023 Australia          460.4            1.54                0.41                -5.52
 2024 Australia          462.9            1.52                0.54                -1.30
 2014     China         3873.9           82.45                 NaN                  NaN
 2015     China         3746.5           82.10               -3.29                -0.42
 2016     China         3410.6           80.38               -8.97                -2.10
 2017     China         3523.6           78.03                3.31                -2.92
 2018     China         3697.7           78.90                4.94                 1.11
 2019     China         3846.3           80.47                4.02                 1.99
 2020     China         3901.6           82.52                1.44                 2.55
 2021     China         4125.8           84.25                5.75                 2.10
 2022     China         4558.6           87.54               10.49                 3.91
 2023     China         4723.3           87.83                3.61                 0.33
 2024     China         4780.0           92.16                1.20                 4.93
 2014     India          646.2           14.44                 NaN                  NaN
 2015     India          674.2           15.84                4.33                 9.70
 2016     India          689.8           16.17                2.31                 2.08
 2017     India          711.7           16.52                3.17                 2.16
 2018     India          760.4           17.05                6.84                 3.21
 2019     India          753.9           17.93               -0.85                 5.16
 2020     India          760.2           17.96                0.84                 0.17
 2021     India          812.1           16.97                6.83                -5.51
 2022     India          910.8           19.27               12.15                13.55
 2023     India         1011.3           20.03               11.03                 3.94
 2024     India         1085.1           22.97                7.30                14.68
 2014 Indonesia          458.1            1.59                 NaN                  NaN
 2015 Indonesia          461.6            1.69                0.76                 6.29
 2016 Indonesia          461.2            1.92               -0.09                13.61
 2017 Indonesia          461.2            1.96                0.00                 2.08
 2018 Indonesia          557.8            2.04               20.95                 4.08
 2019 Indonesia          616.2            2.36               10.47                15.69
 2020 Indonesia          563.7            2.88               -8.52                22.03
 2021 Indonesia          614.0            2.76                8.92                -4.17
 2022 Indonesia          687.4            2.75               11.95                -0.36
 2023 Indonesia          775.2            4.38               12.77                59.27
 2024 Indonesia          836.1            4.72                7.86                 7.76
 2014     Japan            1.3            5.07                 NaN                  NaN
 2015     Japan            1.2            4.99               -7.69                -1.58
 2016     Japan            1.3            5.03                8.33                 0.80
 2017     Japan            1.4            5.02                7.69                -0.20
 2018     Japan            1.0            5.10              -28.57                 1.59
 2019     Japan            0.8            4.99              -20.00                -2.16
 2020     Japan            0.8            4.91                0.00                -1.60
 2021     Japan            0.7            4.57              -12.50                -6.92
 2022     Japan            0.7            4.93                0.00                 7.88
 2023     Japan            0.5            4.92              -28.57                -0.20
 2024     Japan            0.5            4.53                0.00                -7.93
```

## Q5: In how many years did supply and demand move in opposite directions?

```
  country  years_compared  both_up  both_down  opposite_directions
Australia              10        0          4                    6
Indonesia              10        5          0                    4
    India              10        8          0                    2
    Japan              10        1          4                    2
    China              10        7          2                    1
```

## Q6: Largest exporters and importers in the latest year, with implied world trade total

```
trade_role     country  trade_ej  share_pct  implied_world_trade_ej  rank_in_role
  Exporter   Indonesia     10.72       29.8                   35.97             1
  Exporter   Australia      9.07       25.2                   35.99             2
  Importer       China     11.62       32.3                   35.98             1
  Importer       India      5.30       14.7                   36.05             2
  Importer       Japan      4.35       12.1                   35.95             3
  Importer South Korea      3.07        8.5                   36.12             4
```

## Q7: Change in trade volume and world share between the two years (only countries listed in both years)

```
trade_role     country  trade_prev_year_ej  trade_latest_ej  yoy_change_pct  share_change_pp
  Importer       China               10.16            11.62           14.37              3.6
  Exporter   Indonesia               10.00            10.72            7.20              1.6
  Exporter   Australia                9.00             9.07            0.78             -0.2
  Importer       Japan                4.39             4.35           -0.91             -0.3
  Importer       India                5.35             5.30           -0.93             -0.4
  Importer South Korea                3.19             3.07           -3.76             -0.5
```

## Q8: Data gap check: countries listed in the earlier year but missing from the latest year

```
trade_role            country  listed_in_year
  Exporter Russian Federation            2023
```

## Q9: Trade volume relative to domestic consumption (EJ / EJ, so units are consistent)

```
trade_role   country  trade_ej  consumption_ej  trade_to_consumption_ratio
  Exporter Australia      9.07            1.52                        5.97
  Exporter Indonesia     10.72            4.72                        2.27
  Importer     Japan      4.35            4.53                        0.96
  Importer     India      5.30           22.97                        0.23
  Importer     China     11.62           92.16                        0.13
```

## Q10: Trade concentration per year and role (HHI is a lower bound because only listed countries are included)

```
 year trade_role  countries_listed  combined_share_pct  top_share_pct  hhi_lower_bound
 2023   Exporter                 3                68.8           28.2           1671.0
 2024   Exporter                 2                55.0           29.8           1523.0
 2023   Importer                 4                65.2           28.7           1286.0
 2024   Importer                 4                67.6           32.3           1478.0
```

## Q11: Benchmark price: YoY change, distance from the peak and index to the first year

```
 year  price_usd_mt  yoy_change_pct  pct_vs_peak  index_first_year
 2021         138.1             NaN       -59.96             100.0
 2022         344.9          149.75         0.00             249.7
 2023         172.8          -49.90       -49.90             125.1
 2024         136.1          -21.24       -60.54              98.6
 2025         108.4          -20.35       -68.57              78.5
```

## Q12: Did price moves line up with demand growth in China and India?

```
 year  price_yoy_pct  china_consumption_yoy_pct  india_consumption_yoy_pct
 2022          149.7                        3.9                       13.6
 2023          -49.9                        0.3                        3.9
 2024          -21.2                        4.9                       14.7
```

## Q13: Data quality: year coverage per country (expect 11 years each)

```
    dataset   country  n_years  first_year  last_year
consumption Australia       11        2014       2024
consumption     China       11        2014       2024
consumption     India       11        2014       2024
consumption Indonesia       11        2014       2024
consumption     Japan       11        2014       2024
 production Australia       11        2014       2024
 production     China       11        2014       2024
 production     India       11        2014       2024
 production Indonesia       11        2014       2024
 production     Japan       11        2014       2024
```

## Q14: Data quality: consumption moves above 40 percent in one year (verify against source)

```
 year   country  consumption_ej  prev_ej  yoy_pct
 2023 Indonesia            4.38     2.75     59.3
```
