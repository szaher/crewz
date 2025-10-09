# Default Examples - CrewAI Platform

This document describes the default flows and crews that come pre-configured with your CrewAI platform.

## 🎯 Overview

The platform includes working examples based on popular CrewAI use cases:
- **1 Default Flow:** "Research to Article Workflow"
- **1 Default Crew:** "Research Team"
- **3 Default Agents:** Research Analyst, Content Writer, Travel Expert
- **3 Default Tools:** Web Search, File Reader, Calculator
- **1 Default LLM Provider:** OpenAI GPT-4 (requires API key configuration)

---

## 🔄 Default Flow: "Research to Article Workflow"

### Description
A complete workflow that takes a research topic, conducts comprehensive research, validates quality, and produces a publication-ready article.

### Visual Flow
```
┌─────────────────────┐
│  Research Topic     │ (Input)
│  - topic: string    │
│  - depth: string    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Research Phase      │ (Agent: Research Analyst)
│ Conduct research    │
│ Find latest trends  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Quality Gate       │ (Condition)
│  word_count >= 500  │
│  citations >= 3     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Content Writing     │ (Agent: Content Writer)
│ Create article      │
│ 800-1200 words      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Final Article     │ (Output)
│  - article: string  │
│  - word_count: num  │
│  - citations: array │
│  - metadata: object │
└─────────────────────┘
```

### Nodes

**1. Input Node - "Research Topic"**
- **Type:** input
- **Purpose:** Collect research parameters
- **Inputs:**
  - `topic` (string, required): The subject to research
  - `depth` (string, optional): Research depth level (default: "comprehensive")

**2. Agent Node - "Research Phase"**
- **Type:** agent
- **Agent:** Research Analyst
- **Task:** "Conduct comprehensive research on {topic}. Focus on the latest developments, key players, and future trends. Depth: {depth}"
- **Expected Output:** "A detailed research report with citations, statistics, and actionable insights"
- **Tools:** Web Search
- **Temperature:** 0.7

**3. Condition Node - "Quality Gate"**
- **Type:** condition
- **Condition:** `word_count >= 500 && citations >= 3`
- **Purpose:** Ensure research meets minimum quality standards
- **Description:** Validates that research has sufficient depth and credibility

**4. Agent Node - "Content Writing"**
- **Type:** agent
- **Agent:** Content Writer
- **Task:** "Using the research provided, write an engaging and informative article about {topic}. Make it accessible yet authoritative."
- **Expected Output:** "A well-structured article (800-1200 words) with introduction, body sections, and conclusion"
- **Temperature:** 0.8

**5. Output Node - "Final Article"**
- **Type:** output
- **Purpose:** Deliver completed content
- **Outputs:**
  - `article` (string): The complete article text
  - `word_count` (number): Total word count
  - `citations` (array): List of sources cited
  - `metadata` (object): Additional information about the article

### How to Use

1. **Navigate to the Flow:**
   ```
   http://localhost:3001/flows/7
   ```

2. **Click "Execute"**

3. **Provide Input:**
   ```json
   {
     "topic": "Artificial Intelligence Safety",
     "depth": "comprehensive"
   }
   ```

4. **Monitor Execution:**
   - Watch real-time progress
   - View agent outputs
   - Check quality gate validation

5. **Review Output:**
   - Read generated article
   - View citations
   - Check metadata

---

## 👥 Default Crew: "Research Team"

### Description
A two-agent crew that works sequentially to research topics and create content.

### Configuration
- **Name:** Research Team
- **Process:** Sequential
- **Memory:** Enabled
- **Verbose:** True
- **Manager LLM:** OpenAI GPT-4

### Agents (in order)

**1. Research Analyst**
- **Role:** Senior Research Analyst
- **Goal:** Uncover cutting-edge developments and provide comprehensive research
- **Backstory:** Works at a leading tech think tank, expert in identifying emerging trends
- **Tools:** Web Search
- **Delegation:** Disabled
- **Temperature:** 0.7

**2. Content Writer**
- **Role:** Tech Content Strategist
- **Goal:** Craft compelling content on tech advancements
- **Backstory:** Renowned for insightful and engaging articles that make complex concepts accessible
- **Tools:** None
- **Delegation:** Disabled
- **Temperature:** 0.8

### How to Use

1. **Navigate to the Crew:**
   ```
   http://localhost:3001/crews/2
   ```

2. **Execute with Task:**
   - Provide a research topic
   - Agents will execute sequentially
   - Research Analyst gathers information
   - Content Writer creates the article

---

## 🤖 Default Agents

### 1. Research Analyst
**Created for:** Research and information gathering

**Configuration:**
- **Role:** Senior Research Analyst
- **Goal:** Uncover cutting-edge developments and provide comprehensive research
- **Backstory:** Expert at identifying emerging trends and dissecting complex data
- **Tools:** Web Search
- **LLM:** OpenAI GPT-4
- **Temperature:** 0.7 (balanced)
- **Max Iterations:** 15
- **Delegation:** No

**Best Used For:**
- Market research
- Technology trend analysis
- Competitive intelligence
- Data gathering

### 2. Content Writer
**Created for:** Creating engaging written content

**Configuration:**
- **Role:** Tech Content Strategist
- **Goal:** Craft compelling content that engages and educates readers
- **Backstory:** Transforms complex concepts into compelling narratives
- **Tools:** None (pure writing)
- **LLM:** OpenAI GPT-4
- **Temperature:** 0.8 (creative)
- **Max Iterations:** 15
- **Delegation:** No

**Best Used For:**
- Article writing
- Blog posts
- Documentation
- Marketing content

### 3. Travel Expert
**Created for:** Travel planning and logistics

**Configuration:**
- **Role:** Amazing Travel Concierge
- **Goal:** Create amazing travel itineraries with budget and packing suggestions
- **Backstory:** Decades of experience, traveled worldwide
- **Tools:** None
- **LLM:** OpenAI GPT-4
- **Temperature:** 0.7
- **Max Iterations:** 15
- **Delegation:** Yes (can delegate tasks)

**Best Used For:**
- Trip planning
- Itinerary creation
- Budget estimation
- Packing lists

---

## 🔧 Default Tools

### 1. Web Search
- **Type:** Built-in
- **Description:** Search the web for current information using DuckDuckGo
- **Input:** `query` (string)
- **Output:** `results` (array)
- **Used By:** Research Analyst

### 2. File Reader
- **Type:** Built-in
- **Description:** Read and analyze file contents
- **Input:** `file_path` (string)
- **Output:** `content` (string)
- **Used By:** None (available for assignment)

### 3. Calculator
- **Type:** Built-in
- **Description:** Perform mathematical calculations
- **Input:** `expression` (string)
- **Output:** `result` (number)
- **Used By:** None (available for assignment)

---

## 🔑 LLM Provider Configuration

### Default Provider: OpenAI GPT-4

**Status:** Created but requires API key

**Configuration Needed:**
1. Navigate to Settings > LLM Providers
2. Find "OpenAI GPT-4"
3. Click Edit
4. Enter your OpenAI API key
5. Click "Test Connection"
6. Save

**Current Configuration:**
- **Provider Type:** OpenAI
- **Model:** gpt-4
- **API Key:** `sk-placeholder-replace-with-real-key` ⚠️ **REPLACE THIS**
- **Active:** Yes
- **Default:** Yes

**Where to Get API Key:**
- Visit: https://platform.openai.com/api-keys
- Create new secret key
- Copy and paste into the platform

---

## 📊 Example Use Cases

### Use Case 1: Research a Technology
**Flow:** Research to Article Workflow

**Input:**
```json
{
  "topic": "Quantum Computing in 2025",
  "depth": "comprehensive"
}
```

**Expected Result:**
- 800-1200 word article
- Multiple citations
- Latest trends and developments
- Future predictions

**Estimated Time:** 2-5 minutes

---

### Use Case 2: Create Content on AI
**Flow:** Research to Article Workflow

**Input:**
```json
{
  "topic": "Large Language Models and Their Impact",
  "depth": "intermediate"
}
```

**Expected Result:**
- Technical but accessible article
- Real-world examples
- Expert insights
- Practical implications

**Estimated Time:** 2-5 minutes

---

### Use Case 3: Analyze Market Trends
**Crew:** Research Team

**Task:**
```
Analyze the current state of the electric vehicle market,
focusing on key players, technological innovations, and
market projections for the next 5 years.
```

**Expected Result:**
- Comprehensive market analysis
- Key player overview
- Technology assessment
- Future projections

**Estimated Time:** 3-7 minutes

---

## 🛠️ Customizing Defaults

### Modify the Flow

1. **Open Flow Editor:**
   ```
   http://localhost:3001/flows/7
   ```

2. **Make Changes:**
   - Add/remove nodes
   - Change agent tasks
   - Adjust conditions
   - Modify inputs/outputs

3. **Save:**
   - Click Save button
   - Changes persist immediately

### Modify the Crew

1. **Open Crew Page:**
   ```
   http://localhost:3001/crews/2
   ```

2. **Edit Configuration:**
   - Add/remove agents
   - Change process (Sequential → Hierarchical)
   - Toggle memory/verbose
   - Reorder agents

3. **Save Changes**

### Create Your Own

Use the defaults as templates:
1. Duplicate the flow or crew
2. Modify agents and tasks
3. Test with your use case
4. Save as new example

---

## 🔄 Recreating Defaults

If you delete the defaults or want to reset:

```bash
# Run the creation script again
docker-compose exec backend bash -c "cd /app && PYTHONPATH=/app python3 scripts/create_defaults.py"
```

**Note:** Script is idempotent - it won't create duplicates if defaults already exist.

---

## 📝 Notes

### Quality Gate
The condition node checks:
- **Word Count:** At least 500 words
- **Citations:** At least 3 sources

If these criteria aren't met, the flow may:
- Skip the writing phase
- Request additional research
- Fail with validation error

### Agent Collaboration
In the crew:
1. **Research Analyst** runs first
2. Output is passed to **Content Writer**
3. Sequential execution ensures clean handoff

### Best Practices
- **Start with defaults** to understand the platform
- **Modify gradually** to fit your needs
- **Test thoroughly** before production use
- **Keep API keys secure** (never commit to git)

---

## 🎯 Next Steps

1. ✅ **Configure LLM Provider** - Add your OpenAI API key
2. ✅ **Test Default Flow** - Run with sample input
3. ✅ **Explore Default Crew** - See sequential execution
4. ✅ **Create Custom Workflow** - Build your own flow
5. ✅ **Add More Agents** - Expand your team

---

## 🐛 Troubleshooting

### Flow Execution Fails
**Problem:** Flow doesn't execute
**Solution:**
- Check LLM provider API key is valid
- Verify agents are properly configured
- Check execution logs for errors

### No Defaults Visible
**Problem:** Can't find default flow/crew
**Solution:**
```bash
# Recreate defaults
docker-compose exec backend bash -c "cd /app && PYTHONPATH=/app python3 scripts/create_defaults.py"
```

### Quality Gate Always Fails
**Problem:** Condition never passes
**Solution:**
- Adjust condition thresholds
- Modify agent task to produce longer output
- Check research agent is producing citations

---

**🎉 You now have working examples to explore the CrewAI platform!**

Start with the default flow, then customize to fit your needs.
