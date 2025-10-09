# CrewAI Platform - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites
- Docker and Docker Compose installed
- OpenAI API key (get one at https://platform.openai.com/api-keys)

---

## Step 1: Start the Platform (30 seconds)

```bash
cd /Users/blackghost/go/src/github.com/szaher/crewzx/crewz

# Start all services
docker-compose up -d

# Wait for services to be ready (~20 seconds)
docker-compose ps
```

**Expected Output:**
```
NAME               STATUS    PORTS
crewz-backend      running   0.0.0.0:8000->8000/tcp
crewz-frontend     running   0.0.0.0:3001->3001/tcp
crewz-postgres     running   0.0.0.0:5432->5432/tcp
```

---

## Step 2: Create Default Examples (10 seconds)

```bash
# Run the creation script
docker-compose exec backend python3 scripts/create_defaults.py
```

**What Gets Created:**
- ✅ 1 LLM Provider (OpenAI GPT-4)
- ✅ 3 Tools (Web Search, File Reader, Calculator)
- ✅ 3 Agents (Research Analyst, Content Writer, Travel Expert)
- ✅ 1 Crew (Research Team)
- ✅ 1 Flow (Research to Article Workflow)

---

## Step 3: Configure Your API Key (1 minute)

### Option A: Via UI (Recommended)

1. **Open the platform:**
   ```bash
   open http://localhost:3001
   ```

2. **Navigate to LLM Providers:**
   - Click "Settings" in sidebar
   - Click "LLM Providers"
   - Find "OpenAI GPT-4"

3. **Add Your API Key:**
   - Click "Edit"
   - Replace `sk-placeholder-replace-with-real-key` with your actual key
   - Click "Test Connection"
   - Click "Save"

### Option B: Via Database (Advanced)

```bash
docker-compose exec postgres psql -U crewz -d crewz_db -c \
  "UPDATE llm_providers SET api_key='sk-your-key-here' WHERE name='OpenAI GPT-4';"
```

---

## Step 4: Try Your First Flow (2 minutes)

### Via UI

1. **Open the default flow:**
   ```bash
   open http://localhost:3001/flows/7
   ```

2. **Execute the flow:**
   - Click "Execute" button in toolbar
   - Enter this JSON:
   ```json
   {
     "topic": "Artificial Intelligence Safety",
     "depth": "comprehensive"
   }
   ```
   - Click "Execute"

3. **Watch it run:**
   - Real-time logs stream as agents work
   - See research phase complete
   - Watch article being written
   - View final output

### Via API

```bash
curl -X POST http://localhost:8000/api/v1/flows/7/execute \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "topic": "Quantum Computing",
      "depth": "comprehensive"
    }
  }'
```

---

## 🎯 What Can You Do Now?

### 1. Explore Default Examples

**View the Flow:**
```bash
open http://localhost:3001/flows/7
```
- See visual workflow
- Understand agent connections
- Check input/output definitions

**View the Crew:**
```bash
open http://localhost:3001/crews/2
```
- See agent team
- Understand sequential execution
- Review agent configurations

**View the Agents:**
```bash
open http://localhost:3001/agents
```
- Research Analyst - Gathers information
- Content Writer - Creates articles
- Travel Expert - Plans itineraries

**View the Tools:**
```bash
open http://localhost:3001/tools
```
- Web Search - DuckDuckGo integration
- File Reader - Analyze files
- Calculator - Math operations

### 2. Create Your Own Flow

**From Dashboard:**
1. Click "Create Flow" button
2. Enter name and description
3. Click "Create"
4. Add nodes by clicking "Add Node"
5. Connect nodes by dragging handles
6. Click "Save"

**Node Types Available:**
- **Input Node** - Define flow inputs
- **Output Node** - Define flow outputs
- **Agent Node** - Execute agent tasks
- **Condition Node** - Branching logic
- **Tool Node** - Use tools directly

### 3. Build Custom Agents

**Navigate to Agents:**
```bash
open http://localhost:3001/agents/create
```

**Fill in:**
- Name: "My Custom Agent"
- Role: "Data Analyst"
- Goal: "Analyze data and provide insights"
- Backstory: "Expert in data science..."
- LLM Provider: Select "OpenAI GPT-4"
- Tools: Select any tools needed
- Temperature: 0.7 (creativity level)

**Click "Create"**

### 4. Test with Sample Workflows

**Research Workflow:**
```json
{
  "topic": "Climate Change Solutions",
  "depth": "comprehensive"
}
```

**Content Creation:**
```json
{
  "topic": "Future of Work",
  "depth": "intermediate"
}
```

**Market Analysis:**
```json
{
  "topic": "Electric Vehicle Market 2025",
  "depth": "comprehensive"
}
```

---

## 📊 Monitor Your Platform

### View Metrics Dashboard

```bash
open http://localhost:3001/observability
```

**See:**
- Total executions
- Success rate
- Error rate
- Average execution time
- Execution trend chart
- Recent errors list

**Auto-refreshes every 30 seconds**

### Check Logs

```bash
# Backend logs
docker-compose logs -f backend

# Frontend logs
docker-compose logs -f frontend

# All logs
docker-compose logs -f
```

---

## 🔧 Common Tasks

### Stop the Platform

```bash
docker-compose down
```

### Restart Services

```bash
docker-compose restart
```

### View Service Status

```bash
docker-compose ps
```

### Access Database

```bash
docker-compose exec postgres psql -U crewz -d crewz_db
```

### Rebuild After Code Changes

```bash
# Backend only
docker-compose build backend
docker-compose up -d backend

# Frontend only
docker-compose build frontend
docker-compose up -d frontend

# Everything
docker-compose build
docker-compose up -d
```

### Reset Database (Caution!)

```bash
docker-compose down -v
docker-compose up -d
docker-compose exec backend python3 scripts/create_defaults.py
```

---

## 🐛 Troubleshooting

### Services Won't Start

```bash
# Check logs
docker-compose logs

# Try restarting
docker-compose down
docker-compose up -d
```

### Can't Access UI

```bash
# Check if frontend is running
curl http://localhost:3001

# Check frontend logs
docker-compose logs frontend

# Rebuild if needed
docker-compose build frontend
docker-compose up -d frontend
```

### API Errors

```bash
# Check if backend is running
curl http://localhost:8000/health

# Check backend logs
docker-compose logs backend

# Verify database connection
docker-compose exec backend python3 -c "from src.db import SessionLocal; print('DB OK')"
```

### Execution Fails

**Check:**
1. ✅ API key configured correctly
2. ✅ Agents assigned to LLM provider
3. ✅ Tools properly configured
4. ✅ Flow nodes connected

**View Execution Logs:**
```bash
open http://localhost:3001/flows/7/executions
```

---

## 📚 Learn More

### Documentation

- **User Guide:** `DEFAULT_EXAMPLES.md`
- **Implementation Details:** `DEFAULT_EXAMPLES_IMPLEMENTATION.md`
- **UI Features:** `README_UI_FIXES.md`
- **Testing Guide:** `TESTING_GUIDE.md`

### API Documentation

```bash
open http://localhost:8000/docs
```

Interactive Swagger UI with all endpoints documented.

### Architecture

```
┌─────────────────────────────────────────┐
│          Frontend (React)               │
│    http://localhost:3001                │
└───────────────┬─────────────────────────┘
                │ REST API
                ▼
┌─────────────────────────────────────────┐
│         Backend (FastAPI)               │
│    http://localhost:8000                │
└───────────────┬─────────────────────────┘
                │ SQL
                ▼
┌─────────────────────────────────────────┐
│       Database (PostgreSQL)             │
│    localhost:5432                       │
└─────────────────────────────────────────┘
```

---

## 🎯 Example Use Cases

### 1. Research Article (5 minutes)

**Flow:** Research to Article Workflow
**Input:**
```json
{
  "topic": "Quantum Computing Breakthroughs 2025",
  "depth": "comprehensive"
}
```
**Output:** 800-1200 word article with citations

### 2. Market Analysis (7 minutes)

**Crew:** Research Team
**Task:** "Analyze the renewable energy market, focusing on solar and wind power trends for the next 5 years"
**Output:** Comprehensive market report

### 3. Travel Planning (5 minutes)

**Agent:** Travel Expert
**Task:** "Plan a 7-day trip to Japan for a family of 4, budget $5000, interests: culture, food, nature"
**Output:** Detailed itinerary with budget breakdown

---

## 🚀 Next Steps

1. ✅ **Platform running** - Services started
2. ✅ **Defaults created** - Examples populated
3. ✅ **API key configured** - Ready to execute
4. ⏭️ **Run first flow** - Try the research workflow
5. ⏭️ **Create custom flow** - Build your own
6. ⏭️ **Build agents** - Customize for your needs
7. ⏭️ **Production deploy** - Scale up!

---

## 🎉 You're Ready!

Your CrewAI platform is now fully configured with working examples.

**Start here:**
```bash
open http://localhost:3001
```

**Try the default flow:**
```bash
open http://localhost:3001/flows/7
```

**Need help?** Check the documentation files listed above.

---

**Happy Building! 🤖**
