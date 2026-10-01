-- Coal Market & Supply Analytics: business queries (MySQL 8.0+)
-- Each query starts with a "-- Q<n>:" title line. Percent maths uses "* 100.0 /" so results are decimal.

USE coal_market_analytics;

-- Q1: Which selected markets produce the most coal, and what share of the five-market total do they hold?
SELECT country,
       production_mt,
       ROUND(production_mt * 100.0 / SUM(production_mt) OVER (), 2) AS share_of_selected_pct,
       RANK() OVER (ORDER BY production_mt DESC)                    AS production_rank
FROM coal_production
WHERE year = (SELECT MAX(year) FROM coal_production)
ORDER BY production_mt DESC;

-- Q2: Which selected markets consume the most coal (EJ), and what is their share?
SELECT country,
       consumption_ej,
       ROUND(consumption_ej * 100.0 / SUM(consumption_ej) OVER (), 2) AS share_of_selected_pct,
       RANK() OVER (ORDER BY consumption_ej DESC)                     AS consumption_rank
FROM coal_consumption
WHERE year = (SELECT MAX(year) FROM coal_consumption)
ORDER BY consumption_ej DESC;

-- Q3: Long-term growth (CAGR over the full period) for production and consumption, with the growth gap
WITH bounds AS (
    SELECT MIN(year) AS y0, MAX(year) AS y1 FROM v_market
)
SELECT s.country,
       s.production_mt  AS production_start_mt,
       e.production_mt  AS production_end_mt,
       ROUND((POWER(e.production_mt * 1.0 / s.production_mt, 1.0 / (b.y1 - b.y0)) - 1) * 100, 2)   AS production_cagr_pct,
       s.consumption_ej AS consumption_start_ej,
       e.consumption_ej AS consumption_end_ej,
       ROUND((POWER(e.consumption_ej * 1.0 / s.consumption_ej, 1.0 / (b.y1 - b.y0)) - 1) * 100, 2) AS consumption_cagr_pct,
       ROUND((POWER(e.production_mt * 1.0 / s.production_mt, 1.0 / (b.y1 - b.y0))
            - POWER(e.consumption_ej * 1.0 / s.consumption_ej, 1.0 / (b.y1 - b.y0))) * 100, 2)     AS growth_gap_pp
FROM bounds b
JOIN v_market s ON s.year = b.y0
JOIN v_market e ON e.year = b.y1 AND e.country = s.country
ORDER BY production_cagr_pct DESC;

-- Q4: Year-over-year growth in production and consumption (window function LAG)
SELECT year, country, production_mt, consumption_ej,
       ROUND(production_mt  * 100.0 / LAG(production_mt)  OVER (PARTITION BY country ORDER BY year) - 100, 2) AS production_yoy_pct,
       ROUND(consumption_ej * 100.0 / LAG(consumption_ej) OVER (PARTITION BY country ORDER BY year) - 100, 2) AS consumption_yoy_pct
FROM v_market
ORDER BY country, year;

-- Q5: In how many years did supply and demand move in opposite directions?
WITH change AS (
    SELECT year, country,
           production_mt  - LAG(production_mt)  OVER (PARTITION BY country ORDER BY year) AS d_prod,
           consumption_ej - LAG(consumption_ej) OVER (PARTITION BY country ORDER BY year) AS d_cons
    FROM v_market
)
SELECT country,
       COUNT(*)                                                    AS years_compared,
       SUM(CASE WHEN d_prod > 0 AND d_cons > 0 THEN 1 ELSE 0 END)  AS both_up,
       SUM(CASE WHEN d_prod < 0 AND d_cons < 0 THEN 1 ELSE 0 END)  AS both_down,
       SUM(CASE WHEN d_prod * d_cons < 0 THEN 1 ELSE 0 END)        AS opposite_directions
FROM change
WHERE d_prod IS NOT NULL
GROUP BY country
ORDER BY opposite_directions DESC, country;

-- Q6: Largest exporters and importers in the latest year, with implied world trade total
SELECT trade_role, country, trade_ej, share_pct,
       ROUND(trade_ej * 100.0 / share_pct, 2)                         AS implied_world_trade_ej,
       RANK() OVER (PARTITION BY trade_role ORDER BY trade_ej DESC)   AS rank_in_role
FROM coal_trade
WHERE year = (SELECT MAX(year) FROM coal_trade)
ORDER BY trade_role, rank_in_role;

-- Q7: Change in trade volume and world share between the two years (only countries listed in both years)
SELECT t1.trade_role, t1.country,
       t0.trade_ej AS trade_prev_year_ej,
       t1.trade_ej AS trade_latest_ej,
       ROUND(t1.trade_ej * 100.0 / t0.trade_ej - 100, 2) AS yoy_change_pct,
       ROUND(t1.share_pct - t0.share_pct, 2)             AS share_change_pp
FROM coal_trade t1
JOIN coal_trade t0
  ON t0.country = t1.country AND t0.trade_role = t1.trade_role AND t0.year = t1.year - 1
WHERE t1.year = (SELECT MAX(year) FROM coal_trade)
ORDER BY yoy_change_pct DESC;

-- Q8: Data gap check: countries listed in the earlier year but missing from the latest year
SELECT t0.trade_role, t0.country, t0.year AS listed_in_year
FROM coal_trade t0
LEFT JOIN coal_trade t1
  ON t1.country = t0.country AND t1.trade_role = t0.trade_role AND t1.year = t0.year + 1
WHERE t0.year = (SELECT MIN(year) FROM coal_trade)
  AND t1.country IS NULL;

-- Q9: Trade volume relative to domestic consumption (EJ / EJ, so units are consistent)
SELECT t.trade_role, t.country, t.trade_ej, c.consumption_ej,
       ROUND(t.trade_ej * 1.0 / c.consumption_ej, 2) AS trade_to_consumption_ratio
FROM coal_trade t
JOIN coal_consumption c ON c.country = t.country AND c.year = t.year
WHERE t.year = (SELECT MAX(year) FROM coal_trade)
ORDER BY trade_to_consumption_ratio DESC;

-- Q10: Trade concentration per year and role (HHI is a lower bound because only listed countries are included)
SELECT year, trade_role,
       COUNT(*)                      AS countries_listed,
       ROUND(SUM(share_pct), 1)      AS combined_share_pct,
       MAX(share_pct)                AS top_share_pct,
       ROUND(SUM(share_pct * share_pct), 0) AS hhi_lower_bound
FROM coal_trade
GROUP BY year, trade_role
ORDER BY trade_role, year;

-- Q11: Benchmark price: YoY change, distance from the peak and index to the first year
SELECT year, price_usd_mt,
       ROUND(price_usd_mt * 100.0 / LAG(price_usd_mt) OVER (ORDER BY year) - 100, 2) AS yoy_change_pct,
       ROUND(price_usd_mt * 100.0 / MAX(price_usd_mt) OVER () - 100, 2)              AS pct_vs_peak,
       ROUND(price_usd_mt * 100.0 / FIRST_VALUE(price_usd_mt) OVER (ORDER BY year), 1) AS index_first_year
FROM coal_prices_annual
ORDER BY year;

-- Q12: Did price moves line up with demand growth in China and India?
WITH price AS (
    SELECT year, price_usd_mt * 100.0 / LAG(price_usd_mt) OVER (ORDER BY year) - 100 AS price_yoy
    FROM coal_prices_annual
),
demand AS (
    SELECT year, country,
           consumption_ej * 100.0 / LAG(consumption_ej) OVER (PARTITION BY country ORDER BY year) - 100 AS cons_yoy
    FROM coal_consumption
    WHERE country IN ('China', 'India')
)
SELECT p.year,
       ROUND(p.price_yoy, 1) AS price_yoy_pct,
       ROUND(MAX(CASE WHEN d.country = 'China' THEN d.cons_yoy END), 1) AS china_consumption_yoy_pct,
       ROUND(MAX(CASE WHEN d.country = 'India' THEN d.cons_yoy END), 1) AS india_consumption_yoy_pct
FROM price p
JOIN demand d ON d.year = p.year
WHERE p.price_yoy IS NOT NULL
GROUP BY p.year, p.price_yoy
ORDER BY p.year;

-- Q13: Data quality: year coverage per country (expect 11 years each)
SELECT 'production' AS dataset, country, COUNT(*) AS n_years, MIN(year) AS first_year, MAX(year) AS last_year
FROM coal_production GROUP BY country
UNION ALL
SELECT 'consumption', country, COUNT(*), MIN(year), MAX(year)
FROM coal_consumption GROUP BY country
ORDER BY dataset, country;

-- Q14: Data quality: consumption moves above 40 percent in one year (verify against source)
SELECT year, country, consumption_ej, prev_ej, ROUND(consumption_ej * 100.0 / prev_ej - 100, 1) AS yoy_pct
FROM (
    SELECT year, country, consumption_ej,
           LAG(consumption_ej) OVER (PARTITION BY country ORDER BY year) AS prev_ej
    FROM coal_consumption
) x
WHERE prev_ej IS NOT NULL
  AND ABS(consumption_ej * 100.0 / prev_ej - 100) > 40
ORDER BY year;
