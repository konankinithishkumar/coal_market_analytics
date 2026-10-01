-- Coal Market & Supply Analytics: schema (MySQL 8.0+)
-- Safe to re-run: tables are dropped and recreated.

CREATE DATABASE IF NOT EXISTS coal_market_analytics;
USE coal_market_analytics;

DROP VIEW  IF EXISTS v_market;
DROP TABLE IF EXISTS coal_production;
DROP TABLE IF EXISTS coal_consumption;
DROP TABLE IF EXISTS coal_trade;
DROP TABLE IF EXISTS coal_prices_annual;
DROP TABLE IF EXISTS coal_prices_detail;

-- Source: Energy Institute Statistical Review of World Energy 2025. Unit: million tonnes (Mt)
CREATE TABLE coal_production (
    year          INT           NOT NULL,
    country       VARCHAR(100)  NOT NULL,
    production_mt DECIMAL(12,2) NOT NULL,
    PRIMARY KEY (year, country)
);

-- Source: Energy Institute. Unit: exajoules (EJ)
CREATE TABLE coal_consumption (
    year           INT           NOT NULL,
    country        VARCHAR(100)  NOT NULL,
    consumption_ej DECIMAL(12,2) NOT NULL,
    PRIMARY KEY (year, country)
);

-- Source: Energy Institute. Unit: exajoules (EJ), share in % of world trade
CREATE TABLE coal_trade (
    year       INT           NOT NULL,
    trade_role VARCHAR(20)   NOT NULL,
    country    VARCHAR(100)  NOT NULL,
    trade_ej   DECIMAL(12,2) NOT NULL,
    share_pct  DECIMAL(8,2)  NOT NULL,
    PRIMARY KEY (year, trade_role, country)
);

-- Source: World Bank Pink Sheet. Unit: USD per tonne
CREATE TABLE coal_prices_annual (
    year          INT           NOT NULL PRIMARY KEY,
    price_usd_mt  DECIMAL(10,2) NOT NULL
);

-- Quarterly (YYYY-Qn) and monthly (YYYY-MM) prices. Do not average across the two period types.
CREATE TABLE coal_prices_detail (
    period        VARCHAR(10)   NOT NULL PRIMARY KEY,
    price_usd_mt  DECIMAL(10,2) NOT NULL
);

-- Production (Mt) and consumption (EJ) side by side. Units differ, so never subtract one from the other.
CREATE VIEW v_market AS
SELECT p.year, p.country, p.production_mt, c.consumption_ej
FROM coal_production p
JOIN coal_consumption c ON c.year = p.year AND c.country = p.country;
