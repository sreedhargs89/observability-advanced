# Introduction to Observability

## What is Observability?

**Observability** is the ability to understand the internal state of a system by examining its external outputs. In software systems, this means being able to answer questions like:

- "Why is this API endpoint slow?"
- "Which service is causing errors?"
- "What happened during the outage at 2 AM?"
- "How does a request flow through our system?"

## Observability vs Monitoring

Many people confuse monitoring with observability. Here's the key difference:

| Aspect | Monitoring | Observability |
|--------|-----------|---------------|
| **Focus** | Known problems | Unknown problems |
| **Approach** | Predefined dashboards and alerts | Exploratory investigation |
| **Questions** | "Is the system up?" | "Why is it behaving this way?" |
| **Tools** | Health checks, uptime monitors | Logs, metrics, traces |
| **Mindset** | Reactive | Proactive |

### Example Scenario

**Monitoring** tells you: "API response time is 5 seconds (threshold: 1 second) ⚠️"

**Observability** helps you discover:
- Which specific endpoint is slow?
- Is it slow for all users or specific ones?
- Which downstream service is the bottleneck?
- What changed recently that could cause this?

## The Three Pillars of Observability

Observability is built on three fundamental data types:

### 1. 📝 Logs

**What:** Timestamped records of discrete events

**Example:**
```json
{
  "timestamp": "2025-11-21T00:00:00Z",
  "level": "INFO",
  "service": "user-service",
  "message": "User created successfully",
  "user_id": "12345",
  "trace_id": "abc123"
}
```

**Use Cases:**
- Debugging specific errors
- Auditing user actions
- Understanding event sequences

**Strengths:**
- Rich contextual information
- Detailed event history

**Limitations:**
- High volume can be expensive
- Hard to aggregate for trends

---

### 2. 📊 Metrics

**What:** Numerical measurements aggregated over time

**Example:**
```
http_requests_total{service="user-service", status="200"} 1543
http_request_duration_seconds{service="user-service", quantile="0.95"} 0.245
```

**Use Cases:**
- Tracking trends over time
- Setting up alerts
- Capacity planning
- SLA monitoring

**Strengths:**
- Efficient storage
- Great for dashboards
- Easy to alert on

**Limitations:**
- Less detailed than logs
- Can't see individual events

---

### 3. 🔍 Traces

**What:** The journey of a request through distributed services

**Example:**
```
Trace ID: abc123
├─ API Gateway [100ms]
   ├─ User Service [50ms]
   │  └─ Database Query [30ms]
   └─ Order Service [40ms]
      └─ Payment API [35ms]
```

**Use Cases:**
- Understanding service dependencies
- Finding performance bottlenecks
- Debugging distributed systems
- Visualizing request flows

**Strengths:**
- Shows relationships between services
- Pinpoints slow operations
- Reveals cascading failures

**Limitations:**
- Sampling needed at scale
- Requires instrumentation

## Why You Need All Three

Each pillar answers different questions:

| Question | Best Answered By |
|----------|------------------|
| "Is the system healthy?" | **Metrics** |
| "What's the error rate trend?" | **Metrics** |
| "Why did this specific request fail?" | **Logs** + **Traces** |
| "Which service is slow?" | **Traces** |
| "What was the user doing when it failed?" | **Logs** |
| "How do our services interact?" | **Traces** |

### Real-World Example

**Scenario:** Users report slow checkout

1. **Metrics** show: Order service latency p95 is 3 seconds (normally 200ms)
2. **Traces** reveal: Payment API calls are taking 2.8 seconds
3. **Logs** show: Payment API returning "rate limit exceeded" errors

**Root Cause:** Payment provider rate limiting. Solution: Implement retry with backoff.

## Observability in Distributed Systems

Modern applications are distributed across multiple services. This makes observability critical:

### Challenges Without Observability

- **No visibility** into service interactions
- **Difficult debugging** across service boundaries
- **Slow incident response** due to lack of context
- **Blind spots** in performance bottlenecks

### Benefits With Observability

- ✅ **Faster debugging** - Quickly identify root causes
- ✅ **Better reliability** - Detect issues before users do
- ✅ **Improved performance** - Find and fix bottlenecks
- ✅ **Data-driven decisions** - Understand actual usage patterns
- ✅ **Reduced MTTR** (Mean Time To Resolution)

## Key Observability Concepts

### 1. Correlation IDs

A unique identifier that follows a request through all services:

```python
# Request arrives with correlation ID
correlation_id = request.headers.get('X-Correlation-ID', generate_id())

# Include in all logs
logger.info("Processing request", extra={"correlation_id": correlation_id})

# Pass to downstream services
requests.get(url, headers={"X-Correlation-ID": correlation_id})
```

### 2. Structured Logging

Logs in a consistent, parseable format (usually JSON):

```python
# ❌ Unstructured
print("User alice@example.com created order 123")

# ✅ Structured
logger.info("Order created", extra={
    "user_email": "alice@example.com",
    "order_id": 123,
    "event": "order_created"
})
```

### 3. Cardinality

The number of unique values for a metric label:

```python
# ❌ High cardinality (bad - too many unique user IDs)
http_requests_total{user_id="12345"}

# ✅ Low cardinality (good - limited set of endpoints)
http_requests_total{endpoint="/api/users"}
```

### 4. Sampling

Recording only a percentage of traces to reduce overhead:

```python
# Sample 10% of requests
if random.random() < 0.1:
    create_trace()
```

## The Observability Workflow

1. **Instrument** your code with logging, metrics, and tracing
2. **Collect** the data in centralized systems
3. **Visualize** with dashboards and UIs
4. **Alert** on anomalies and thresholds
5. **Investigate** when issues occur
6. **Improve** based on insights

## Tools We'll Use

| Tool | Purpose | Port |
|------|---------|------|
| **Prometheus** | Metrics collection and storage | 9090 |
| **Jaeger** | Distributed tracing backend | 16686 |
| **Grafana** | Visualization and dashboards | 3000 |
| **OpenTelemetry** | Instrumentation library | - |

## What's Next?

Now that you understand the fundamentals, let's dive into each pillar:

- **Next:** [Logging Deep Dive](02-logging.md)
- **Then:** [Metrics Explained](03-metrics.md)
- **Finally:** [Distributed Tracing](04-tracing.md)

## Quick Exercise

Before moving on, think about a recent production issue you've encountered:

1. What questions did you need to answer?
2. Which pillar (logs, metrics, traces) would have helped most?
3. What information was missing?

This mindset will help you appreciate what we're building!

---

**Ready to learn about logging?** Continue to [02-logging.md](02-logging.md) →
