# Phase 3.2 Implementation Plan
## Feedback & Analytics (Weeks 4-6)

**Status**: 🚧 Ready to Implement
**Prerequisites**: ✅ Phase 3.1 Complete
**Estimated Duration**: 2-3 weeks

---

## 📋 Overview

Phase 3.2 adds comprehensive feedback collection and analytics capabilities to the CrewAI Orchestration Platform, enabling users to rate executions, agents, and chat interactions with real-time analytics aggregation.

---

## 🎯 Acceptance Criteria

**From plan3.md:**
> ≥ 100 feedback entries produce accurate rollups and export.

**Detailed Criteria:**
- ✅ Feedback submission API operational
- ✅ Real-time ingestion to ClickHouse working
- ✅ Redis pub/sub events flowing
- ✅ Analytics rollups accurate (ratings, sentiment, trends)
- ✅ Recharts-compatible data endpoints
- ✅ Prometheus metrics exported
- ✅ 100+ test feedback entries processed correctly

---

## 🏗️ Architecture

### Data Flow
```
User Submits Feedback
    ↓
PostgreSQL (transactional storage)
    ↓
Redis Pub/Sub (event notification)
    ↓
ClickHouse Ingestion Worker
    ↓
ClickHouse (analytics storage)
    ↓
Analytics API Endpoints
    ↓
Frontend Dashboard (Recharts)
```

### Storage Strategy

**PostgreSQL**:
- Transactional feedback records
- Relational integrity (user, execution, agent)
- Source of truth

**ClickHouse**:
- Time-series analytics
- Fast aggregations (ratings, sentiment trends)
- Rollup tables for dashboards

**Redis**:
- Pub/Sub for real-time events
- Feedback submission notifications
- Dashboard live updates

---

## 📦 Deliverables

### 1. Data Models

#### PostgreSQL Model (Already Created ✅)
```python
# backend/src/models/feedback.py
class Feedback(BaseModel):
    tenant_id: int
    user_id: int
    feedback_type: FeedbackType  # execution, agent, chat, general
    execution_id: int (nullable)
    agent_id: int (nullable)
    chat_session_id: str (nullable)
    rating: int  # 1-5
    comment: text
    sentiment: SentimentType  # positive, neutral, negative
    sentiment_score: float  # -1.0 to 1.0
    tags: JSON  # ["bug", "performance", "accuracy"]
    metadata: JSON
```

#### ClickHouse Schema
```sql
-- feedback_events table (raw events)
CREATE TABLE feedback_events (
    id UInt64,
    tenant_id UInt32,
    user_id UInt32,
    feedback_type Enum8('execution'=1, 'agent'=2, 'chat'=3, 'general'=4),
    target_id Nullable(UInt32),
    rating UInt8,
    sentiment Enum8('positive'=1, 'neutral'=0, 'negative'=-1),
    sentiment_score Float32,
    tags Array(String),
    created_at DateTime,
    date Date
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (tenant_id, date, created_at);

-- feedback_daily_rollup (materialized view)
CREATE MATERIALIZED VIEW feedback_daily_rollup
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (tenant_id, feedback_type, date)
AS SELECT
    tenant_id,
    feedback_type,
    date,
    count() as feedback_count,
    avg(rating) as avg_rating,
    countIf(sentiment = 'positive') as positive_count,
    countIf(sentiment = 'neutral') as neutral_count,
    countIf(sentiment = 'negative') as negative_count
FROM feedback_events
GROUP BY tenant_id, feedback_type, date;
```

---

### 2. Infrastructure Updates

#### Docker Compose Addition
```yaml
services:
  clickhouse:
    image: clickhouse/clickhouse-server:23.8-alpine
    container_name: crewai-clickhouse
    ports:
      - "8123:8123"  # HTTP interface
      - "9000:9000"  # Native protocol
    environment:
      CLICKHOUSE_DB: crewai_analytics
      CLICKHOUSE_USER: crewai
      CLICKHOUSE_PASSWORD: dev_password
    volumes:
      - clickhouse_data:/var/lib/clickhouse
      - ./infra/clickhouse/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    healthcheck:
      test: ["CMD", "clickhouse-client", "--query", "SELECT 1"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  clickhouse_data:
```

---

### 3. Backend Services

#### Feedback Service
```python
# backend/src/services/feedback_service.py
class FeedbackService:
    def __init__(self, db: Session, redis_client, clickhouse_client):
        self.db = db
        self.redis = redis_client
        self.clickhouse = clickhouse_client

    async def submit_feedback(
        self,
        tenant_id: int,
        user_id: int,
        feedback_data: FeedbackCreate
    ) -> Feedback:
        """
        Submit user feedback.

        1. Save to PostgreSQL
        2. Analyze sentiment (if comment provided)
        3. Publish to Redis
        4. Queue for ClickHouse ingestion
        """
        # Save to PostgreSQL
        feedback = Feedback(
            tenant_id=tenant_id,
            user_id=user_id,
            **feedback_data.dict()
        )

        # Sentiment analysis
        if feedback.comment:
            feedback.sentiment, feedback.sentiment_score = \
                self.analyze_sentiment(feedback.comment)

        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)

        # Publish event
        await self.publish_feedback_event(feedback)

        # Queue for ClickHouse
        await self.queue_for_analytics(feedback)

        return feedback

    def analyze_sentiment(self, text: str) -> tuple[SentimentType, float]:
        """
        Simple sentiment analysis using TextBlob or transformers.
        For production: Use OpenAI/Anthropic API for better accuracy.
        """
        from textblob import TextBlob
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity  # -1 to 1

        if polarity > 0.1:
            sentiment = SentimentType.POSITIVE
        elif polarity < -0.1:
            sentiment = SentimentType.NEGATIVE
        else:
            sentiment = SentimentType.NEUTRAL

        return sentiment, polarity
```

#### ClickHouse Ingestion Worker
```python
# backend/src/services/clickhouse_ingestion.py
class ClickHouseIngestionWorker:
    """
    Background worker to ingest feedback from PostgreSQL/Redis to ClickHouse.
    """

    def __init__(self, redis_client, clickhouse_client):
        self.redis = redis_client
        self.clickhouse = clickhouse_client

    async def start(self):
        """Subscribe to Redis feedback events and ingest to ClickHouse."""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe('feedback:submitted')

        async for message in pubsub.listen():
            if message['type'] == 'message':
                feedback_data = json.loads(message['data'])
                await self.ingest_feedback(feedback_data)

    async def ingest_feedback(self, feedback_data: dict):
        """Insert feedback into ClickHouse."""
        query = """
        INSERT INTO feedback_events (
            id, tenant_id, user_id, feedback_type,
            target_id, rating, sentiment, sentiment_score,
            tags, created_at, date
        ) VALUES
        """

        await self.clickhouse.execute(query, [
            feedback_data['id'],
            feedback_data['tenant_id'],
            feedback_data['user_id'],
            feedback_data['feedback_type'],
            feedback_data.get('execution_id') or feedback_data.get('agent_id'),
            feedback_data['rating'],
            feedback_data['sentiment'],
            feedback_data['sentiment_score'],
            feedback_data['tags'],
            feedback_data['created_at'],
            feedback_data['created_at'].date()
        ])
```

---

### 4. API Endpoints

#### Feedback Submission
```python
# backend/src/api/v1/feedback.py

@router.post("", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(
    request: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """
    Submit feedback on execution, agent, or chat.

    - **feedback_type**: execution, agent, chat, general
    - **execution_id**: (optional) execution to rate
    - **agent_id**: (optional) agent to rate
    - **chat_session_id**: (optional) chat session to rate
    - **rating**: 1-5 stars
    - **comment**: (optional) text feedback
    - **tags**: (optional) categorization tags
    """
    service = FeedbackService(db, get_redis(), get_clickhouse())
    feedback = await service.submit_feedback(
        tenant_id=current_user['tenant_id'],
        user_id=current_user['user_id'],
        feedback_data=request
    )
    return FeedbackResponse.from_orm(feedback)
```

#### Analytics Endpoints
```python
@router.get("/analytics/ratings", response_model=RatingsAnalytics)
async def get_ratings_analytics(
    start_date: datetime,
    end_date: datetime,
    feedback_type: Optional[FeedbackType] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """
    Get rating analytics for time period.

    Returns:
    - Average rating over time
    - Rating distribution (1-5 stars)
    - Feedback count
    - Trend analysis
    """
    service = AnalyticsService(get_clickhouse())
    return await service.get_ratings_analytics(
        tenant_id=current_user['tenant_id'],
        start_date=start_date,
        end_date=end_date,
        feedback_type=feedback_type
    )

@router.get("/analytics/sentiment", response_model=SentimentAnalytics)
async def get_sentiment_analytics(
    start_date: datetime,
    end_date: datetime,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """
    Get sentiment distribution over time.

    Returns:
    - Positive/Neutral/Negative counts
    - Sentiment trend
    - Top negative/positive themes
    """
    service = AnalyticsService(get_clickhouse())
    return await service.get_sentiment_analytics(
        tenant_id=current_user['tenant_id'],
        start_date=start_date,
        end_date=end_date
    )

@router.get("/analytics/usage-trends", response_model=UsageTrends)
async def get_usage_trends(
    period: str = "7d",  # 7d, 30d, 90d
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """
    Get usage trends (feedback volume, engagement).

    Returns:
    - Feedback submissions over time
    - Active users providing feedback
    - Most rated agents/executions
    """
    service = AnalyticsService(get_clickhouse())
    return await service.get_usage_trends(
        tenant_id=current_user['tenant_id'],
        period=period
    )
```

---

### 5. Prometheus Metrics

```python
# backend/src/services/metrics_service.py
from prometheus_client import Counter, Histogram, Gauge

# Feedback metrics
feedback_submissions_total = Counter(
    'feedback_submissions_total',
    'Total feedback submissions',
    ['tenant_id', 'feedback_type']
)

feedback_rating_distribution = Histogram(
    'feedback_rating_distribution',
    'Distribution of feedback ratings',
    ['tenant_id', 'feedback_type'],
    buckets=[1, 2, 3, 4, 5]
)

feedback_sentiment_gauge = Gauge(
    'feedback_sentiment_score',
    'Current sentiment score (-1 to 1)',
    ['tenant_id']
)
```

---

### 6. Database Migrations

#### Alembic Migration
```python
# backend/alembic/versions/xxx_add_feedback_tables.py

def upgrade():
    # Create feedback table
    op.create_table(
        'feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('feedback_type', sa.Enum('EXECUTION', 'AGENT', 'CHAT', 'GENERAL', name='feedbacktype'), nullable=False),
        sa.Column('execution_id', sa.Integer(), nullable=True),
        sa.Column('agent_id', sa.Integer(), nullable=True),
        sa.Column('chat_session_id', sa.String(255), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('sentiment', sa.Enum('POSITIVE', 'NEUTRAL', 'NEGATIVE', name='sentimenttype'), nullable=True),
        sa.Column('sentiment_score', sa.Float(), nullable=True),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['execution_id'], ['executions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes
    op.create_index('ix_feedback_tenant_id', 'feedback', ['tenant_id'])
    op.create_index('ix_feedback_user_id', 'feedback', ['user_id'])
    op.create_index('ix_feedback_type', 'feedback', ['feedback_type'])
    op.create_index('ix_feedback_rating', 'feedback', ['rating'])
    op.create_index('ix_feedback_sentiment', 'feedback', ['sentiment'])
    op.create_index('ix_feedback_created_at', 'feedback', ['created_at'])
```

---

## 📝 Implementation Steps

### Week 1: Infrastructure & Data Models

1. **Day 1-2: ClickHouse Setup**
   - [ ] Add ClickHouse to docker-compose.yml
   - [ ] Create init SQL scripts
   - [ ] Test ClickHouse connectivity
   - [ ] Create feedback_events table
   - [ ] Create materialized views for rollups

2. **Day 3-4: Database Models**
   - [x] Create Feedback model in PostgreSQL
   - [ ] Create Alembic migration
   - [ ] Run migration
   - [ ] Add model to __init__.py
   - [ ] Create Pydantic schemas

3. **Day 5: Redis Pub/Sub**
   - [ ] Create Redis publisher service
   - [ ] Create Redis subscriber worker
   - [ ] Test pub/sub flow

### Week 2: API & Analytics

4. **Day 1-2: Feedback API**
   - [ ] Create FeedbackService
   - [ ] Add sentiment analysis (TextBlob)
   - [ ] Create feedback endpoints
   - [ ] Test feedback submission

5. **Day 3-4: ClickHouse Ingestion**
   - [ ] Create ClickHouse client wrapper
   - [ ] Build ingestion worker
   - [ ] Test real-time ingestion
   - [ ] Verify rollup tables

6. **Day 5: Analytics Queries**
   - [ ] Create AnalyticsService
   - [ ] Build aggregation queries
   - [ ] Test query performance

### Week 3: Dashboards & Testing

7. **Day 1-2: Analytics API**
   - [ ] Create analytics endpoints
   - [ ] Add Recharts-compatible responses
   - [ ] Test with mock data

8. **Day 3: Prometheus Metrics**
   - [ ] Add Prometheus client
   - [ ] Export feedback metrics
   - [ ] Test /metrics endpoint

9. **Day 4-5: Integration Testing**
   - [ ] Generate 100+ test feedback entries
   - [ ] Verify rollup accuracy
   - [ ] Test export functionality
   - [ ] Performance testing

---

## 🧪 Testing Plan

### Unit Tests
- FeedbackService.submit_feedback()
- Sentiment analysis accuracy
- ClickHouse ingestion logic
- Analytics aggregation queries

### Integration Tests
- End-to-end feedback submission → analytics
- Redis pub/sub flow
- ClickHouse rollup accuracy
- 100+ feedback entries test

### Performance Tests
- ClickHouse query performance (< 100ms)
- Redis pub/sub latency (< 10ms)
- Analytics endpoint response time (< 200ms)

---

## 📊 Success Metrics

- ✅ 100+ feedback entries processed
- ✅ Rollups accurate within 1%
- ✅ Real-time ingestion < 5s lag
- ✅ Analytics queries < 100ms
- ✅ Sentiment analysis > 70% accuracy
- ✅ Prometheus metrics exported
- ✅ Dashboard data format compatible with Recharts

---

## 🚀 Deployment Checklist

- [ ] ClickHouse container running
- [ ] ClickHouse schema created
- [ ] PostgreSQL migration applied
- [ ] Redis pub/sub tested
- [ ] Ingestion worker started
- [ ] API endpoints accessible
- [ ] Metrics endpoint live
- [ ] Test data loaded

---

## 📚 Dependencies

**Python Packages** (add to requirements.txt):
```
clickhouse-driver==0.2.6
textblob==0.17.1  # Sentiment analysis
redis==5.0.1  # Already installed
prometheus-client>=0.19.0  # Already installed
```

**Docker Images**:
```
clickhouse/clickhouse-server:23.8-alpine
```

---

## 🎯 Next Phase

After Phase 3.2 completion:
- **Phase 3.3**: Traceability Service (LLM/Tool call logging)
- **Phase 3.4**: Audit & Compliance (hash-chained integrity)
- **Phase 3.5**: Cost Control & Rate Limiting
- **Phase 3.6**: UI Polish & Admin Panel

---

**Status**: Ready for implementation 🚀
**Current**: Feedback model created ✅
**Next**: Add ClickHouse to docker-compose
