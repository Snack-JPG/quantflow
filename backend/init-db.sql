-- QuantFlow TimescaleDB initialization script
-- Create time-series tables with automatic partitioning

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Order book snapshots table
CREATE TABLE IF NOT EXISTS order_book_snapshots (
    time TIMESTAMPTZ NOT NULL,
    exchange VARCHAR(20) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    sequence BIGINT,
    bids JSONB NOT NULL,
    asks JSONB NOT NULL,
    mid_price DECIMAL(20, 8),
    spread DECIMAL(20, 8),
    best_bid DECIMAL(20, 8),
    best_ask DECIMAL(20, 8),
    bid_volume DECIMAL(30, 8),
    ask_volume DECIMAL(30, 8)
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('order_book_snapshots', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Create index for efficient queries
CREATE INDEX IF NOT EXISTS idx_order_book_exchange_symbol_time
ON order_book_snapshots (exchange, symbol, time DESC);

-- Trades table
CREATE TABLE IF NOT EXISTS trades (
    time TIMESTAMPTZ NOT NULL,
    exchange VARCHAR(20) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    trade_id VARCHAR(100) NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    quantity DECIMAL(30, 8) NOT NULL,
    side VARCHAR(4) NOT NULL, -- buy/sell
    UNIQUE(exchange, trade_id)
);

-- Convert to hypertable
SELECT create_hypertable('trades', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Create index
CREATE INDEX IF NOT EXISTS idx_trades_exchange_symbol_time
ON trades (exchange, symbol, time DESC);

-- Microstructure metrics table
CREATE TABLE IF NOT EXISTS microstructure_metrics (
    time TIMESTAMPTZ NOT NULL,
    exchange VARCHAR(20) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    metric_name VARCHAR(50) NOT NULL,
    value DECIMAL(30, 10),
    window_minutes INTEGER
);

-- Convert to hypertable
SELECT create_hypertable('microstructure_metrics', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Create index
CREATE INDEX IF NOT EXISTS idx_metrics_exchange_symbol_metric_time
ON microstructure_metrics (exchange, symbol, metric_name, time DESC);

-- Alerts table
CREATE TABLE IF NOT EXISTS alerts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    pattern VARCHAR(50) NOT NULL,
    severity VARCHAR(10) NOT NULL,
    confidence DECIMAL(3, 2) NOT NULL,
    exchange VARCHAR(20) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    context JSONB,
    explanation TEXT,
    ai_generated BOOLEAN DEFAULT FALSE
);

-- Create index
CREATE INDEX IF NOT EXISTS idx_alerts_time ON alerts (time DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_pattern ON alerts (pattern, time DESC);

-- Backtest results table
CREATE TABLE IF NOT EXISTS backtest_results (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    strategy_name VARCHAR(100) NOT NULL,
    config JSONB NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    total_return DECIMAL(10, 4),
    sharpe_ratio DECIMAL(10, 4),
    sortino_ratio DECIMAL(10, 4),
    max_drawdown DECIMAL(10, 4),
    win_rate DECIMAL(10, 4),
    profit_factor DECIMAL(10, 4),
    trades_count INTEGER,
    equity_curve JSONB,
    trade_log JSONB
);

-- Create continuous aggregates for faster queries
-- 1-minute aggregates
CREATE MATERIALIZED VIEW IF NOT EXISTS order_book_1min
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', time) AS bucket,
    exchange,
    symbol,
    AVG(mid_price) as avg_mid_price,
    AVG(spread) as avg_spread,
    MAX(bid_volume) as max_bid_volume,
    MAX(ask_volume) as max_ask_volume,
    COUNT(*) as sample_count
FROM order_book_snapshots
GROUP BY bucket, exchange, symbol
WITH NO DATA;

-- 5-minute aggregates
CREATE MATERIALIZED VIEW IF NOT EXISTS order_book_5min
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('5 minutes', time) AS bucket,
    exchange,
    symbol,
    AVG(mid_price) as avg_mid_price,
    AVG(spread) as avg_spread,
    MAX(bid_volume) as max_bid_volume,
    MAX(ask_volume) as max_ask_volume,
    COUNT(*) as sample_count
FROM order_book_snapshots
GROUP BY bucket, exchange, symbol
WITH NO DATA;

-- Add retention policies (keep raw data for 7 days, aggregates longer)
SELECT add_retention_policy('order_book_snapshots', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_retention_policy('trades', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_retention_policy('microstructure_metrics', INTERVAL '30 days', if_not_exists => TRUE);

-- Add compression policy (compress data older than 1 day)
SELECT add_compression_policy('order_book_snapshots', INTERVAL '1 day', if_not_exists => TRUE);
SELECT add_compression_policy('trades', INTERVAL '1 day', if_not_exists => TRUE);

-- Add continuous aggregate refresh policies
SELECT add_continuous_aggregate_policy('order_book_1min',
    start_offset => INTERVAL '10 minutes',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute',
    if_not_exists => TRUE
);

SELECT add_continuous_aggregate_policy('order_book_5min',
    start_offset => INTERVAL '30 minutes',
    end_offset => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '5 minutes',
    if_not_exists => TRUE
);