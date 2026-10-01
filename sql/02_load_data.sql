-- Load the raw CSV files into MySQL.
-- Run from the project root so the relative paths resolve, with local_infile enabled:
--   mysql --local-infile=1 -u <user> -p < sql/02_load_data.sql
-- (the server also needs: SET GLOBAL local_infile = 1)

USE coal_market_analytics;

LOAD DATA LOCAL INFILE 'data/raw/coal_production_ei_2014_2024.csv'
INTO TABLE coal_production
FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n' IGNORE 1 LINES
(year, country, production_mt);

LOAD DATA LOCAL INFILE 'data/raw/coal_consumption_ei_2014_2024.csv'
INTO TABLE coal_consumption
FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n' IGNORE 1 LINES
(year, country, consumption_ej);

LOAD DATA LOCAL INFILE 'data/raw/coal_trade_selected_2023_2024.csv'
INTO TABLE coal_trade
FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n' IGNORE 1 LINES
(year, trade_role, country, trade_ej, share_pct);

LOAD DATA LOCAL INFILE 'data/raw/coal_price_worldbank_2021_2025.csv'
INTO TABLE coal_prices_annual
FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n' IGNORE 1 LINES
(year, price_usd_mt);

LOAD DATA LOCAL INFILE 'data/raw/coal_price_detail_worldbank.csv'
INTO TABLE coal_prices_detail
FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n' IGNORE 1 LINES
(period, price_usd_mt);

-- Quick row-count check: expect 55, 55, 13, 5, 10
SELECT 'coal_production' AS tbl, COUNT(*) AS n FROM coal_production
UNION ALL SELECT 'coal_consumption', COUNT(*) FROM coal_consumption
UNION ALL SELECT 'coal_trade', COUNT(*) FROM coal_trade
UNION ALL SELECT 'coal_prices_annual', COUNT(*) FROM coal_prices_annual
UNION ALL SELECT 'coal_prices_detail', COUNT(*) FROM coal_prices_detail;
