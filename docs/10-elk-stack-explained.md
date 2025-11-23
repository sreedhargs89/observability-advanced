# The ELK Stack: Complete Guide from Basics

## Table of Contents
1. [What is the ELK Stack?](#1-what-is-the-elk-stack)
2. [The Three Components Explained](#2-the-three-components-explained)
3. [How ELK Works Together](#3-how-elk-works-together)
4. [ELK vs Loki (PLG Stack)](#4-elk-vs-loki-plg-stack)
5. [When to Use ELK vs Loki](#5-when-to-use-elk-vs-loki)
6. [Setting Up ELK Stack](#6-setting-up-elk-stack)
7. [Real-World Use Cases](#7-real-world-use-cases)
8. [Best Practices](#8-best-practices)

---

## 1. What is the ELK Stack?

**ELK** is an acronym for three open-source projects:
- **E**lasticsearch - Search and analytics engine
- **L**ogstash - Data processing pipeline
- **K**ibana - Visualization and exploration tool

Later, **Beats** was added, making it the **Elastic Stack** (but people still call it ELK).

### The Simple Explanation

Think of ELK like a library system:
- **Logstash** = The librarian who collects and organizes books
- **Elasticsearch** = The library's catalog and storage system
- **Kibana** = The search interface where you find what you need

### What Problem Does ELK Solve?

**The Problem:**
```
You have 100 microservices running in production.
Each service generates logs.
An error occurs.
You need to find which service caused it.

Without ELK:
- SSH into 100 different servers
- Run `tail -f /var/log/app.log` on each
- Manually search for error messages
- Try to correlate timestamps across services
Time: Hours or days
```

**With ELK:**
```
1. Open Kibana
2. Search: "error" AND "payment" AND timestamp:[now-1h TO now]
3. See all matching logs from all services
4. Filter by service, severity, user ID, etc.
Time: Seconds
```

---

## 2. The Three Components Explained

### 2.1 Elasticsearch

**What it is:** A distributed search and analytics engine built on Apache Lucene.

**Think of it as:** Google for your logs.

#### Key Features:

1. **Full-Text Search**
   ```json
   // Search for "payment failed" across millions of logs
   GET /logs/_search
   {
     "query": {
       "match": {
         "message": "payment failed"
       }
     }
   }
   ```

2. **Structured Data Storage**
   ```json
   // Each log is stored as a JSON document
   {
     "timestamp": "2025-11-23T16:00:00Z",
     "level": "ERROR",
     "service": "order-service",
     "message": "Payment gateway timeout",
     "user_id": "12345",
     "order_id": "67890"
   }
   ```

3. **Distributed Architecture**
   ```
   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
   │   Node 1    │  │   Node 2    │  │   Node 3    │
   │  (Primary)  │  │  (Replica)  │  │  (Replica)  │
   └─────────────┘  └─────────────┘  └─────────────┘
   ```
   - Data is split across multiple nodes (shards)
   - Replicas ensure high availability
   - Scales horizontally

4. **Inverted Index**
   ```
   Traditional Database:
   Doc 1: "The quick brown fox"
   Doc 2: "The lazy dog"
   
   Inverted Index:
   "quick" → [Doc 1]
   "brown" → [Doc 1]
   "fox"   → [Doc 1]
   "lazy"  → [Doc 2]
   "dog"   → [Doc 2]
   
   Search for "fox" → Instant lookup in index → Doc 1
   ```

#### How Elasticsearch Stores Logs:

```
Index: logs-2025-11-23
├─ Shard 0
│  ├─ Document 1: {"timestamp": "...", "message": "User login"}
│  ├─ Document 2: {"timestamp": "...", "message": "Order created"}
│  └─ ...
├─ Shard 1
│  ├─ Document 1000: {"timestamp": "...", "message": "Payment failed"}
│  └─ ...
└─ Shard 2
   └─ ...
```

#### Why It's Powerful:

**Example Query:**
```json
// Find all ERROR logs from order-service in the last hour
// where payment failed for premium users
GET /logs/_search
{
  "query": {
    "bool": {
      "must": [
        {"match": {"level": "ERROR"}},
        {"match": {"service": "order-service"}},
        {"match": {"message": "payment failed"}},
        {"match": {"user.tier": "premium"}}
      ],
      "filter": {
        "range": {
          "timestamp": {
            "gte": "now-1h"
          }
        }
      }
    }
  }
}
```

**Result:** Milliseconds to search through billions of logs!

---

### 2.2 Logstash

**What it is:** A data processing pipeline that ingests, transforms, and sends data to Elasticsearch.

**Think of it as:** A smart data plumber that cleans and routes your logs.

#### The Three Stages:

```
┌─────────┐    ┌─────────┐    ┌─────────┐
│  INPUT  │ →  │ FILTER  │ →  │ OUTPUT  │
└─────────┘    └─────────┘    └─────────┘
```

#### 1. INPUT - Collect Data

**Sources:**
- Files (`/var/log/app.log`)
- Syslog
- Beats (lightweight shippers)
- HTTP endpoints
- Kafka, Redis, RabbitMQ
- Databases
- Cloud services (S3, CloudWatch)

**Example:**
```ruby
input {
  # Read from a file
  file {
    path => "/var/log/app.log"
    start_position => "beginning"
  }
  
  # Listen on TCP port
  tcp {
    port => 5000
  }
  
  # Read from Kafka
  kafka {
    bootstrap_servers => "kafka:9092"
    topics => ["logs"]
  }
}
```

#### 2. FILTER - Transform Data

**What it does:**
- Parse unstructured logs into structured JSON
- Add fields, remove fields, rename fields
- Enrich data (add geolocation, lookup user info)
- Filter out noise

**Example: Parsing Apache Logs**

**Raw Log:**
```
127.0.0.1 - - [23/Nov/2025:16:00:00 +0000] "GET /api/users HTTP/1.1" 200 1234
```

**Logstash Filter:**
```ruby
filter {
  grok {
    match => {
      "message" => "%{COMBINEDAPACHELOG}"
    }
  }
  
  date {
    match => ["timestamp", "dd/MMM/yyyy:HH:mm:ss Z"]
  }
  
  geoip {
    source => "clientip"
  }
}
```

**Structured Output:**
```json
{
  "clientip": "127.0.0.1",
  "timestamp": "2025-11-23T16:00:00Z",
  "method": "GET",
  "request": "/api/users",
  "httpversion": "1.1",
  "response": 200,
  "bytes": 1234,
  "geoip": {
    "country_name": "United States",
    "city_name": "San Francisco"
  }
}
```

**Example: Parsing JSON Logs**

**Raw Log:**
```json
{"timestamp":"2025-11-23T16:00:00Z","level":"ERROR","service":"order-service","message":"Payment failed","user_id":"123"}
```

**Logstash Filter:**
```ruby
filter {
  json {
    source => "message"
  }
  
  # Add a field
  mutate {
    add_field => {
      "environment" => "production"
    }
  }
  
  # Remove sensitive data
  mutate {
    remove_field => ["user_password", "credit_card"]
  }
}
```

#### 3. OUTPUT - Send Data

**Destinations:**
- Elasticsearch (most common)
- Files
- Kafka
- S3
- Email
- Slack
- PagerDuty

**Example:**
```ruby
output {
  # Send to Elasticsearch
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "logs-%{+YYYY.MM.dd}"
  }
  
  # Also send errors to Slack
  if [level] == "ERROR" {
    slack {
      url => "https://hooks.slack.com/services/..."
      channel => "#alerts"
      username => "LogstashBot"
    }
  }
}
```

#### Complete Logstash Configuration Example:

```ruby
input {
  beats {
    port => 5044
  }
}

filter {
  # Parse JSON logs
  json {
    source => "message"
  }
  
  # Add correlation ID if missing
  if ![correlation_id] {
    uuid {
      target => "correlation_id"
    }
  }
  
  # Parse stack traces
  if [level] == "ERROR" {
    mutate {
      gsub => [
        "message", "\n", " | "
      ]
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "logs-%{[service]}-%{+YYYY.MM.dd}"
  }
  
  stdout {
    codec => rubydebug
  }
}
```

---

### 2.3 Kibana

**What it is:** A web interface for visualizing and exploring data in Elasticsearch.

**Think of it as:** The dashboard and search UI for your logs.

#### Key Features:

#### 1. Discover - Search Logs

**Interface:**
```
┌─────────────────────────────────────────────────────┐
│ Search: level:ERROR AND service:order-service      │
│ Time: Last 15 minutes                              │
├─────────────────────────────────────────────────────┤
│ 2025-11-23 16:00:00 | ERROR | order-service       │
│ Payment gateway timeout: Unable to reach provider  │
│ user_id: 123, order_id: 456                        │
├─────────────────────────────────────────────────────┤
│ 2025-11-23 15:58:30 | ERROR | order-service       │
│ Database connection failed                          │
│ ...                                                 │
└─────────────────────────────────────────────────────┘
```

**Search Syntax:**
```
# Simple search
payment failed

# Field search
level:ERROR

# Boolean operators
level:ERROR AND service:order-service

# Wildcards
user_id:123*

# Range queries
timestamp:[now-1h TO now]

# Exists
_exists_:error_code

# Complex query
(level:ERROR OR level:CRITICAL) AND service:order-service AND NOT message:timeout
```

#### 2. Visualize - Create Charts

**Types of Visualizations:**
- Line charts (trends over time)
- Bar charts (comparisons)
- Pie charts (distributions)
- Data tables
- Metrics (single numbers)
- Heat maps
- Tag clouds

**Example: Error Rate Over Time**
```
┌─────────────────────────────────────────┐
│     Errors per Minute                   │
│                                         │
│  100 ┤                           ╭─╮   │
│   80 ┤                       ╭───╯ │   │
│   60 ┤                   ╭───╯     │   │
│   40 ┤               ╭───╯         │   │
│   20 ┤           ╭───╯             │   │
│    0 ┴───────────╯─────────────────╯   │
│      10:00  11:00  12:00  13:00  14:00 │
└─────────────────────────────────────────┘
```

#### 3. Dashboard - Combine Visualizations

**Example Dashboard:**
```
┌────────────────────────────────────────────────────┐
│  Production Monitoring Dashboard                   │
├────────────────────────────────────────────────────┤
│ ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│ │ Total    │  │ Error    │  │ Response │         │
│ │ Requests │  │ Rate     │  │ Time     │         │
│ │ 1.2M     │  │ 2.3%     │  │ 245ms    │         │
│ └──────────┘  └──────────┘  └──────────┘         │
│                                                    │
│ ┌────────────────────────────────────────┐        │
│ │  Requests per Minute (Line Chart)      │        │
│ │  ╭─╮     ╭─╮                           │        │
│ │  │ │ ╭───╯ ╰─╮                         │        │
│ │  ╰─╯─╯       ╰─╮                       │        │
│ └────────────────────────────────────────┘        │
│                                                    │
│ ┌──────────────┐  ┌──────────────────────┐        │
│ │ Top Errors   │  │ Service Health       │        │
│ │ (Pie Chart)  │  │ (Table)              │        │
│ └──────────────┘  └──────────────────────┘        │
└────────────────────────────────────────────────────┘
```

#### 4. Alerting - Get Notified

**Example Alert:**
```yaml
Alert: High Error Rate
Condition: 
  - Error count > 100 in last 5 minutes
  - Service: order-service
Actions:
  - Send email to ops@company.com
  - Post to Slack #alerts
  - Create PagerDuty incident
```

---

## 3. How ELK Works Together

### The Complete Flow:

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Applications                         │
│  (API Gateway, User Service, Order Service)                 │
└────────────┬────────────────────────────────────────────────┘
             │ Logs to files or stdout
             ▼
┌─────────────────────────────────────────────────────────────┐
│                         Beats                                │
│  (Filebeat, Metricbeat, etc. - Lightweight log shippers)   │
└────────────┬────────────────────────────────────────────────┘
             │ Ships logs
             ▼
┌─────────────────────────────────────────────────────────────┐
│                       Logstash                               │
│  - Receives logs from Beats                                 │
│  - Parses unstructured logs → structured JSON               │
│  - Enriches data (add fields, geoip, etc.)                 │
│  - Filters out noise                                        │
└────────────┬────────────────────────────────────────────────┘
             │ Sends structured data
             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Elasticsearch                             │
│  - Indexes logs for fast searching                          │
│  - Stores data across multiple nodes                        │
│  - Provides search API                                      │
└────────────┬────────────────────────────────────────────────┘
             │ Query API
             ▼
┌─────────────────────────────────────────────────────────────┐
│                        Kibana                                │
│  - Web UI for searching logs                                │
│  - Create visualizations and dashboards                     │
│  - Set up alerts                                            │
└─────────────────────────────────────────────────────────────┘
             │
             ▼
         👤 You (the user)
```

### Real-World Example:

**Scenario:** User reports "checkout is broken"

**Step 1: Application logs the error**
```python
# order-service/app.py
logger.error("Payment processing failed", extra={
    "user_id": "123",
    "order_id": "456",
    "error": "Gateway timeout"
})
```

**Step 2: Filebeat ships the log**
```
[2025-11-23T16:00:00Z] ERROR order-service Payment processing failed user_id=123 order_id=456 error="Gateway timeout"
```

**Step 3: Logstash parses and enriches**
```json
{
  "timestamp": "2025-11-23T16:00:00Z",
  "level": "ERROR",
  "service": "order-service",
  "message": "Payment processing failed",
  "user_id": "123",
  "order_id": "456",
  "error": "Gateway timeout",
  "environment": "production",
  "host": "order-service-pod-abc123"
}
```

**Step 4: Elasticsearch indexes**
```
Index: logs-order-service-2025.11.23
Document ID: abc-123-def
Content: {... the JSON above ...}
```

**Step 5: You search in Kibana**
```
Search: user_id:123 AND level:ERROR
Result: Found 1 document
```

**Step 6: You see the error**
```
┌─────────────────────────────────────────┐
│ 2025-11-23 16:00:00                     │
│ ERROR | order-service                   │
│ Payment processing failed               │
│ user_id: 123                            │
│ order_id: 456                           │
│ error: Gateway timeout                  │
└─────────────────────────────────────────┘
```

**Total time:** 30 seconds from error to discovery!

---

## 4. ELK vs Loki (PLG Stack)

### Architecture Comparison:

#### ELK Stack:
```
Application → Filebeat → Logstash → Elasticsearch → Kibana
```

#### PLG Stack (What we use):
```
Application → Promtail → Loki → Grafana
```

### Key Differences:

| Feature | ELK (Elasticsearch) | PLG (Loki) |
|---------|-------------------|-----------|
| **Indexing** | Full-text index of log content | Only indexes metadata (labels) |
| **Storage** | High (indexes everything) | Low (stores compressed logs) |
| **Cost** | Expensive (needs powerful hardware) | Cheap (minimal resources) |
| **Search Speed** | Very fast (pre-indexed) | Slower (scans logs at query time) |
| **Query Language** | Lucene / KQL | LogQL (like PromQL) |
| **Best For** | Complex searches, analytics | Simple searches, cost-sensitive |
| **Scalability** | Horizontal (add more nodes) | Horizontal (add more nodes) |
| **Learning Curve** | Steep | Moderate |

### Storage Comparison:

**Example: 1 million log lines**

**ELK (Elasticsearch):**
```
Raw logs: 100 MB
Inverted index: 300 MB
Metadata: 50 MB
Total: 450 MB
```

**Loki:**
```
Raw logs (compressed): 20 MB
Labels index: 5 MB
Total: 25 MB
```

**Loki uses ~18x less storage!**

### Query Comparison:

**Find all ERROR logs from order-service in the last hour:**

**ELK (Kibana Query Language):**
```
level:ERROR AND service:order-service AND timestamp:[now-1h TO now]
```

**Loki (LogQL):**
```
{service="order-service"} |= "ERROR" [1h]
```

**Find logs containing "payment" and "timeout":**

**ELK:**
```
message:(payment AND timeout)
```

**Loki:**
```
{service="order-service"} |= "payment" |= "timeout"
```

**Count errors by service:**

**ELK:**
```json
GET /logs/_search
{
  "size": 0,
  "query": {
    "match": {"level": "ERROR"}
  },
  "aggs": {
    "by_service": {
      "terms": {"field": "service"}
    }
  }
}
```

**Loki:**
```
sum(count_over_time({level="ERROR"}[1h])) by (service)
```

---

## 5. When to Use ELK vs Loki

### Use ELK When:

✅ **You need complex searches**
```
Example: "Find all logs where payment failed for premium users 
in California who ordered laptops on Black Friday"

ELK: Easy with full-text search
Loki: Difficult (requires many labels)
```

✅ **You need analytics and aggregations**
```
Example: "What's the average response time by endpoint and region?"

ELK: Built-in aggregations
Loki: Limited aggregation capabilities
```

✅ **You have structured data**
```
Example: E-commerce transactions, user events, API logs

ELK: Excellent for structured JSON
Loki: Better for simple text logs
```

✅ **You need compliance/audit logs**
```
Example: Financial transactions, healthcare records

ELK: Better retention, search, and export capabilities
Loki: Limited long-term retention features
```

✅ **Budget is not a constraint**
```
ELK: Requires powerful servers (16GB+ RAM per node)
Loki: Runs on minimal resources
```

### Use Loki When:

✅ **Cost is a concern**
```
Loki: 10-20x cheaper storage
ELK: Expensive at scale
```

✅ **You already use Prometheus and Grafana**
```
Loki: Same query language (LogQL ~ PromQL)
Loki: Same UI (Grafana)
ELK: Different stack, different UI
```

✅ **Simple log searches are enough**
```
Example: "Show me errors from order-service"

Loki: Perfect for this
ELK: Overkill
```

✅ **You're running Kubernetes**
```
Loki: Native Kubernetes support
Loki: Automatic pod label extraction
ELK: Requires more configuration
```

✅ **You want simplicity**
```
Loki: 2 components (Promtail, Loki)
ELK: 3-4 components (Beats, Logstash, Elasticsearch, Kibana)
```

### Hybrid Approach:

Many companies use **both**:

```
┌─────────────────────────────────────────┐
│         Application Logs                │
└────────────┬────────────────────────────┘
             │
      ┌──────┴──────┐
      ▼             ▼
┌──────────┐  ┌──────────┐
│   Loki   │  │   ELK    │
│          │  │          │
│ Recent   │  │ Long-term│
│ logs     │  │ archive  │
│ (7 days) │  │ (90 days)│
└──────────┘  └──────────┘
```

**Strategy:**
- **Loki**: Real-time debugging (last 7 days)
- **ELK**: Long-term storage and analytics (90+ days)

---

## 6. Setting Up ELK Stack

### Docker Compose Example:

```yaml
version: '3.8'

services:
  # Elasticsearch - Search and storage
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    container_name: elasticsearch
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
      - xpack.security.enabled=false
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data
    networks:
      - elk

  # Logstash - Data processing
  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    container_name: logstash
    volumes:
      - ./logstash/config/logstash.yml:/usr/share/logstash/config/logstash.yml
      - ./logstash/pipeline:/usr/share/logstash/pipeline
    ports:
      - "5044:5044"  # Beats input
      - "5000:5000"  # TCP input
    environment:
      - "LS_JAVA_OPTS=-Xmx256m -Xms256m"
    networks:
      - elk
    depends_on:
      - elasticsearch

  # Kibana - Visualization
  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    container_name: kibana
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    networks:
      - elk
    depends_on:
      - elasticsearch

  # Filebeat - Log shipper
  filebeat:
    image: docker.elastic.co/beats/filebeat:8.11.0
    container_name: filebeat
    user: root
    volumes:
      - ./filebeat/filebeat.yml:/usr/share/filebeat/filebeat.yml
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      - elk
    depends_on:
      - logstash

networks:
  elk:
    driver: bridge

volumes:
  elasticsearch-data:
```

### Logstash Configuration:

**logstash/pipeline/logstash.conf:**
```ruby
input {
  beats {
    port => 5044
  }
}

filter {
  # Parse JSON logs
  if [message] =~ /^\{.*\}$/ {
    json {
      source => "message"
    }
  }
  
  # Add timestamp
  date {
    match => ["timestamp", "ISO8601"]
    target => "@timestamp"
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "logs-%{[service]}-%{+YYYY.MM.dd}"
  }
  
  stdout {
    codec => rubydebug
  }
}
```

### Filebeat Configuration:

**filebeat/filebeat.yml:**
```yaml
filebeat.inputs:
  - type: container
    paths:
      - '/var/lib/docker/containers/*/*.log'

processors:
  - add_docker_metadata:
      host: "unix:///var/run/docker.sock"
  - decode_json_fields:
      fields: ["message"]
      target: ""
      overwrite_keys: true

output.logstash:
  hosts: ["logstash:5044"]
```

### Start the Stack:

```bash
docker-compose up -d
```

### Access:
- **Elasticsearch**: http://localhost:9200
- **Kibana**: http://localhost:5601

---

## 7. Real-World Use Cases

### Use Case 1: E-Commerce Platform

**Company:** Online retailer with 1000 microservices

**Requirements:**
- Track all user actions (clicks, purchases, searches)
- Analyze conversion funnels
- Detect fraud patterns
- Compliance (keep logs for 7 years)

**Solution:** ELK Stack
- **Why:** Complex analytics, long retention, structured data
- **Cost:** $50,000/month
- **Benefit:** Prevented $2M in fraud annually

### Use Case 2: Startup SaaS

**Company:** 10-person startup, 5 microservices

**Requirements:**
- Debug production errors
- Monitor API performance
- Keep costs low

**Solution:** Loki (PLG Stack)
- **Why:** Simple, cheap, integrates with existing Grafana
- **Cost:** $100/month
- **Benefit:** Same observability as ELK at 1% of the cost

### Use Case 3: Financial Services

**Company:** Bank with strict compliance

**Requirements:**
- Audit all transactions
- Search historical data (10 years)
- Complex queries for fraud detection
- High availability (99.99%)

**Solution:** ELK Stack with S3 archival
- **Why:** Compliance, complex search, long retention
- **Cost:** $200,000/month
- **Benefit:** Regulatory compliance, fraud prevention

---

## 8. Best Practices

### For ELK:

#### 1. Index Management
```
✅ Use time-based indices: logs-2025-11-23
✅ Set up index lifecycle management (ILM)
✅ Delete old indices automatically
❌ Don't use a single massive index
```

#### 2. Mapping Templates
```json
{
  "index_patterns": ["logs-*"],
  "template": {
    "mappings": {
      "properties": {
        "timestamp": {"type": "date"},
        "level": {"type": "keyword"},
        "message": {"type": "text"},
        "user_id": {"type": "keyword"}
      }
    }
  }
}
```

#### 3. Resource Allocation
```
Elasticsearch:
- Heap: 50% of RAM (max 32GB)
- Disk: SSD recommended
- CPU: 8+ cores for production

Logstash:
- Heap: 1-4GB
- CPU: 4+ cores
```

#### 4. Security
```yaml
✅ Enable authentication (X-Pack)
✅ Use TLS/SSL
✅ Restrict network access
✅ Encrypt data at rest
```

### For Loki:

#### 1. Label Strategy
```
✅ Use low-cardinality labels:
   {service="order-service", environment="production"}

❌ Don't use high-cardinality labels:
   {user_id="123", request_id="abc-def"}
```

#### 2. Retention
```yaml
# loki-config.yml
limits_config:
  retention_period: 168h  # 7 days

table_manager:
  retention_deletes_enabled: true
  retention_period: 168h
```

#### 3. Resource Allocation
```
Loki:
- RAM: 2-4GB
- Disk: Regular HDD is fine
- CPU: 2-4 cores
```

---

## Summary

### ELK Stack:
- **E**lasticsearch: Search engine and storage
- **L**ogstash: Data processing pipeline
- **K**ibana: Visualization and UI

### When to Use:
- **ELK**: Complex searches, analytics, compliance, budget available
- **Loki**: Simple searches, cost-sensitive, already using Grafana

### Key Takeaway:
```
ELK = Powerful but expensive
Loki = Simple and cheap

Choose based on your needs, not hype!
```

---

## Next Steps

1. **Try ELK**: Set up the Docker Compose example
2. **Compare**: Run both ELK and Loki side-by-side
3. **Decide**: Choose based on your requirements
4. **Optimize**: Follow best practices for your chosen stack

**Remember:** The best logging stack is the one that solves YOUR problems at a cost YOU can afford!
