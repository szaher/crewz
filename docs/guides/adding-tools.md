# Tool Integration Guide

## Overview

Tools extend agent capabilities by executing custom code in isolated Docker containers. This guide covers creating, registering, and using custom tools.

## Tool Concepts

### What is a Tool?

A tool is a containerized function that:
- Accepts structured inputs (JSON schema)
- Performs specific tasks (API calls, data processing, etc.)
- Returns structured outputs
- Runs in isolated Docker environment

### Use Cases

- **API Integrations**: Call external services (Stripe, SendGrid, etc.)
- **Data Processing**: Parse CSV, transform JSON, analyze images
- **Web Scraping**: Extract data from websites
- **File Operations**: Generate PDFs, process documents
- **Custom Logic**: Business-specific computations

## Creating a Tool

### Step 1: Define Tool Schema

Create a JSON schema describing inputs and outputs:

```json
{
  "name": "web_scraper",
  "description": "Scrapes content from a URL and extracts structured data",
  "inputs": {
    "type": "object",
    "properties": {
      "url": {
        "type": "string",
        "description": "URL to scrape"
      },
      "selectors": {
        "type": "object",
        "description": "CSS selectors for data extraction",
        "properties": {
          "title": {"type": "string"},
          "content": {"type": "string"}
        }
      }
    },
    "required": ["url", "selectors"]
  },
  "outputs": {
    "type": "object",
    "properties": {
      "title": {"type": "string"},
      "content": {"type": "string"},
      "scraped_at": {"type": "string", "format": "date-time"}
    }
  }
}
```

### Step 2: Write Tool Code

Create Python script that reads inputs and writes outputs:

**tool.py:**
```python
#!/usr/bin/env python3
"""
Web Scraper Tool

Reads inputs from /input.json
Writes outputs to /output.json
"""

import json
import sys
from datetime import datetime
from bs4 import BeautifulSoup
import requests

def main():
    # Read inputs
    with open('/input.json', 'r') as f:
        inputs = json.load(f)

    url = inputs['url']
    selectors = inputs['selectors']

    # Fetch webpage
    response = requests.get(url, timeout=10)
    response.raise_for_status()

    # Parse HTML
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract data using selectors
    outputs = {
        'title': soup.select_one(selectors['title']).text.strip(),
        'content': soup.select_one(selectors['content']).text.strip(),
        'scraped_at': datetime.utcnow().isoformat()
    }

    # Write outputs
    with open('/output.json', 'w') as f:
        json.dump(outputs, f, indent=2)

    print("✅ Web scraping completed successfully")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        error_output = {
            'error': str(e),
            'type': type(e).__name__
        }
        with open('/output.json', 'w') as f:
            json.dump(error_output, f, indent=2)
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
```

### Step 3: Create Dockerfile

Package tool with dependencies:

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

# Install dependencies
RUN pip install --no-cache-dir \
    requests==2.31.0 \
    beautifulsoup4==4.12.2 \
    lxml==4.9.3

# Copy tool script
COPY tool.py /tool.py
RUN chmod +x /tool.py

# Set working directory
WORKDIR /

# Entrypoint
ENTRYPOINT ["python3", "/tool.py"]
```

### Step 4: Register Tool

```bash
# Build Docker image
docker build -t my-web-scraper:latest .

# Push to registry (if using remote)
docker tag my-web-scraper:latest registry.example.com/my-web-scraper:latest
docker push registry.example.com/my-web-scraper:latest

# Register via API
curl -X POST http://localhost:8000/api/v1/tools \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "web_scraper",
    "description": "Scrapes content from websites",
    "docker_image": "my-web-scraper:latest",
    "schema": {
      "inputs": {...},
      "outputs": {...}
    },
    "is_active": true
  }'
```

## Using Tools in Flows

### Add Tool Node to Flow

```json
{
  "nodes": [
    {
      "id": "scrape_article",
      "type": "tool",
      "tool_id": "web_scraper",
      "inputs": {
        "url": "{input.article_url}",
        "selectors": {
          "title": "h1.article-title",
          "content": "div.article-body"
        }
      }
    },
    {
      "id": "summarize",
      "type": "agent",
      "agent_id": "summarizer",
      "task": "Summarize the scraped article",
      "context": ["{scrape_article.output.content}"]
    }
  ],
  "edges": [
    {"source": "scrape_article", "target": "summarize"}
  ]
}
```

### Execute Flow with Tool

```bash
curl -X POST http://localhost:8000/api/v1/flows/{flow_id}/execute \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "inputs": {
      "article_url": "https://example.com/article"
    }
  }'
```

## Example Tools

### 1. PDF Generator

**Purpose:** Convert HTML/Markdown to PDF

**tool.py:**
```python
import json
from weasyprint import HTML

def main():
    with open('/input.json') as f:
        inputs = json.load(f)

    html_content = inputs['html']
    output_path = '/output.pdf'

    HTML(string=html_content).write_pdf(output_path)

    outputs = {
        'pdf_path': output_path,
        'size_bytes': os.path.getsize(output_path)
    }

    with open('/output.json', 'w') as f:
        json.dump(outputs, f)

if __name__ == '__main__':
    main()
```

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libpango-1.0-0 libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install weasyprint==60.1

COPY tool.py /tool.py
ENTRYPOINT ["python3", "/tool.py"]
```

### 2. Email Sender

**Purpose:** Send emails via SendGrid

**tool.py:**
```python
import json
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def main():
    with open('/input.json') as f:
        inputs = json.load(f)

    message = Mail(
        from_email=inputs['from_email'],
        to_emails=inputs['to_email'],
        subject=inputs['subject'],
        html_content=inputs['body']
    )

    sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
    response = sg.send(message)

    outputs = {
        'status_code': response.status_code,
        'message_id': response.headers.get('X-Message-Id')
    }

    with open('/output.json', 'w') as f:
        json.dump(outputs, f)

if __name__ == '__main__':
    main()
```

### 3. Database Query Tool

**Purpose:** Execute SQL queries (read-only)

**tool.py:**
```python
import json
import psycopg2

def main():
    with open('/input.json') as f:
        inputs = json.load(f)

    conn = psycopg2.connect(
        host=os.environ['DB_HOST'],
        database=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD']
    )

    cursor = conn.cursor()
    cursor.execute(inputs['query'])

    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()

    outputs = {
        'columns': columns,
        'rows': [dict(zip(columns, row)) for row in rows],
        'row_count': len(rows)
    }

    cursor.close()
    conn.close()

    with open('/output.json', 'w') as f:
        json.dump(outputs, f)

if __name__ == '__main__':
    main()
```

## Security Best Practices

### 1. Input Validation

```python
def validate_inputs(inputs: dict):
    """Validate inputs against schema."""
    # Check required fields
    required = ['url', 'selectors']
    for field in required:
        if field not in inputs:
            raise ValueError(f"Missing required field: {field}")

    # Validate URL format
    if not inputs['url'].startswith(('http://', 'https://')):
        raise ValueError("Invalid URL format")

    # Sanitize inputs
    inputs['url'] = inputs['url'].strip()
```

### 2. Resource Limits

Configure CPU/memory limits in Kubernetes:

```yaml
resources:
  limits:
    cpu: "1"
    memory: "512Mi"
  requests:
    cpu: "100m"
    memory: "128Mi"
```

### 3. Network Isolation

Tools have no network access by default:

```python
# To enable network access, explicitly configure
tool_config = {
    "network_enabled": True,
    "allowed_domains": ["api.stripe.com", "api.sendgrid.com"]
}
```

### 4. Timeout Enforcement

```python
# Tool execution timeout (enforced by platform)
tool_config = {
    "timeout": 60  # seconds
}
```

## Testing Tools Locally

### Run Tool Manually

```bash
# Create test input
cat > input.json <<EOF
{
  "url": "https://example.com",
  "selectors": {
    "title": "h1",
    "content": "p"
  }
}
EOF

# Build image
docker build -t my-web-scraper .

# Run container
docker run --rm \
  -v $(pwd)/input.json:/input.json \
  -v $(pwd)/output:/output \
  my-web-scraper

# Check output
cat output/output.json
```

### Automated Testing

```python
# tests/test_web_scraper_tool.py

import json
import subprocess

def test_web_scraper_tool():
    """Test web scraper with mock data."""

    # Prepare input
    inputs = {
        "url": "https://example.com",
        "selectors": {
            "title": "h1",
            "content": "p"
        }
    }

    with open('input.json', 'w') as f:
        json.dump(inputs, f)

    # Run tool
    result = subprocess.run(
        ['docker', 'run', '--rm',
         '-v', f'{os.getcwd()}/input.json:/input.json',
         '-v', f'{os.getcwd()}/output:/output',
         'my-web-scraper'],
        capture_output=True
    )

    assert result.returncode == 0

    # Verify output
    with open('output/output.json') as f:
        outputs = json.load(f)

    assert 'title' in outputs
    assert 'content' in outputs
```

## Tool Registry

View available tools:

```bash
# List all tools
curl http://localhost:8000/api/v1/tools \
  -H "Authorization: Bearer $TOKEN"

# Get tool details
curl http://localhost:8000/api/v1/tools/{tool_id} \
  -H "Authorization: Bearer $TOKEN"
```

## Troubleshooting

### Tool Timeout

**Issue:** Tool execution exceeds timeout

**Solution:**
- Optimize tool code for performance
- Increase timeout in tool config
- Break into smaller sub-tools

### Container Fails to Start

**Issue:** "Error: failed to start container"

**Solution:**
```bash
# Test container locally
docker run -it my-tool /bin/sh

# Check logs
docker logs <container_id>
```

### Output Not Generated

**Issue:** `/output.json` missing

**Solution:**
- Ensure tool writes to `/output.json`
- Check file permissions
- Verify error handling writes output

## Best Practices

1. **Single Responsibility**: Each tool does one thing well
2. **Fail Fast**: Validate inputs early, return clear errors
3. **Idempotent**: Running tool multiple times produces same result
4. **Stateless**: No side effects, no persistent state
5. **Documented**: Clear schema with descriptions

## Next Steps

- [Create Flows with Tools](./creating-flows.md)
- [Deploy to Kubernetes](./deploying-k8s.md)
- [Review Security Model](../architecture/security-model.md)
