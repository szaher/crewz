-- ClickHouse initialization script for CrewAI Analytics
-- Creates feedback analytics tables and materialized views

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS crewai_analytics;

USE crewai_analytics;

-- Raw feedback events table
CREATE TABLE IF NOT EXISTS feedback_events (
    id UInt64,
    tenant_id UInt32,
    user_id UInt32,
    feedback_type Enum8('execution'=1, 'agent'=2, 'chat'=3, 'general'=4),
    target_id Nullable(UInt32),
    rating UInt8,
    sentiment Enum8('positive'=1, 'neutral'=0, 'negative'=-1),
    sentiment_score Float32,
    tags Array(String),
    comment String,
    created_at DateTime,
    date Date
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (tenant_id, date, created_at)
SETTINGS index_granularity = 8192;

-- Daily rollup materialized view
CREATE MATERIALIZED VIEW IF NOT EXISTS feedback_daily_rollup
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (tenant_id, feedback_type, date)
AS SELECT
    tenant_id,
    feedback_type,
    date,
    count() as feedback_count,
    avg(rating) as avg_rating,
    min(rating) as min_rating,
    max(rating) as max_rating,
    countIf(sentiment = 'positive') as positive_count,
    countIf(sentiment = 'neutral') as neutral_count,
    countIf(sentiment = 'negative') as negative_count,
    avg(sentiment_score) as avg_sentiment_score
FROM feedback_events
GROUP BY tenant_id, feedback_type, date;

-- Hourly rollup for real-time dashboards
CREATE MATERIALIZED VIEW IF NOT EXISTS feedback_hourly_rollup
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (tenant_id, feedback_type, date, hour)
AS SELECT
    tenant_id,
    feedback_type,
    date,
    toHour(created_at) as hour,
    count() as feedback_count,
    avg(rating) as avg_rating,
    countIf(sentiment = 'positive') as positive_count,
    countIf(sentiment = 'neutral') as neutral_count,
    countIf(sentiment = 'negative') as negative_count
FROM feedback_events
GROUP BY tenant_id, feedback_type, date, hour;

-- Target-specific rollup (by execution, agent, etc.)
CREATE MATERIALIZED VIEW IF NOT EXISTS feedback_by_target_rollup
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (tenant_id, feedback_type, date, target_id_non_null)
AS SELECT
    tenant_id,
    feedback_type,
    coalesce(target_id, 0) as target_id_non_null,
    date,
    count() as feedback_count,
    avg(rating) as avg_rating,
    countIf(sentiment = 'positive') as positive_count,
    countIf(sentiment = 'neutral') as neutral_count,
    countIf(sentiment = 'negative') as negative_count
FROM feedback_events
WHERE target_id IS NOT NULL
GROUP BY tenant_id, feedback_type, date, target_id_non_null;

-- Tag frequency rollup for trend analysis
CREATE MATERIALIZED VIEW IF NOT EXISTS feedback_tag_frequency
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (tenant_id, tag, date)
AS SELECT
    tenant_id,
    arrayJoin(tags) as tag,
    date,
    count() as tag_count,
    avg(rating) as avg_rating_with_tag
FROM feedback_events
WHERE length(tags) > 0
GROUP BY tenant_id, tag, date;
