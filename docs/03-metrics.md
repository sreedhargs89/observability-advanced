# Metrics Explained

Metrics are numerical measurements that help you understand system behavior over time. Unlike logs (which are discrete events), metrics are aggregated data points.

## Why Metrics?

**Logs** answer: "What happened to request XYZ?"  
**Metrics** answer: "How is the system performing overall?"

### Example

Instead of reading 10,000 log lines to see if your API is healthy, check one metric:

```
http_requests_total{status="500"} / http_requests_total = 0.02  # 2% error rate
```

## Types of Metrics

### 1. Counter

A value that only **increases** (or resets to zero).

**Examples:**
- Total HTTP requests
- Total errors
- Total orders processed

```python
from prometheus_client import Counter

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# Increment the counter
http_requests_total.labels(method='GET', endpoint='/users', status='200').inc()
```

**Prometheus Query:**
```promql
# Rate of requests per second
rate(http_requests_total[5m])

# Total requests in last hour
increase(http_requests_total[1h])
```

---

### 2. Gauge

A value that can **go up or down**.

**Examples:**
- Current memory usage
- Number of active connections
- Queue size

```python
from prometheus_client import Gauge

active_connections = Gauge(
    'active_connections',
    'Number of active connections',
    ['service']
)

# Set the gauge
active_connections.labels(service='user-service').set(42)

# Increment/decrement
active_connections.labels(service='user-service').inc()
active_connections.labels(service='user-service').dec()
```

**Prometheus Query:**
```promql
# Current value
active_connections{service="user-service"}

# Average over 5 minutes
avg_over_time(active_connections[5m])
```

---

### 3. Histogram

Tracks the **distribution** of values (e.g., request durations).

**Examples:**
- Request latency
- Response size
- Query duration

```python
from prometheus_client import Histogram

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]  # Custom buckets
)

# Observe a value
with http_request_duration_seconds.labels(method='GET', endpoint='/users').time():
    # Your code here
    process_request()
```

**Prometheus Query:**
```promql
# 95th percentile latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Average latency
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])
```

---

### 4. Summary

Similar to histogram but calculates quantiles on the client side.

```python
from prometheus_client import Summary

request_latency = Summary(
    'request_latency_seconds',
    'Request latency in seconds',
    ['endpoint']
)

# Observe a value
request_latency.labels(endpoint='/users').observe(0.245)
```

**When to use:**
- Histogram: Better for aggregation across instances
- Summary: Better for pre-calculated quantiles

## The RED Method

A simple framework for monitoring services:

### **R**ate
How many requests per second?

```promql
rate(http_requests_total[5m])
```

### **E**rrors
How many requests are failing?

```promql
rate(http_requests_total{status=~"5.."}[5m])
```

### **D**uration
How long do requests take?

```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

## Metric Labels

Labels add dimensions to metrics:

```python
http_requests_total.labels(
    method='POST',
    endpoint='/orders',
    status='201'
).inc()
```

**Result:**
```
http_requests_total{method="POST", endpoint="/orders", status="201"} 1543
```

### Label Best Practices

#### ✅ Good Labels (Low Cardinality)

```python
# Limited set of values
http_requests_total.labels(
    method='GET',           # ~10 values
    endpoint='/users',      # ~50 values
    status='200'           # ~10 values
)
```

#### ❌ Bad Labels (High Cardinality)

```python
# Too many unique values!
http_requests_total.labels(
    user_id='12345',       # Millions of values ❌
    request_id='abc-123',  # Infinite values ❌
    timestamp='2025-11-21' # Infinite values ❌
)
```

**Why?** High cardinality causes:
- Memory exhaustion
- Slow queries
- Storage issues

## Metrics in Our Services

Let's look at the user service:

```python
from prometheus_client import Counter, Histogram, Gauge
import time

# Counter: Total requests
requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# Histogram: Request duration
request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

# Gauge: Active requests
active_requests = Gauge(
    'http_requests_active',
    'Active HTTP requests'
)

@app.route('/users', methods=['POST'])
def create_user():
    active_requests.inc()
    start_time = time.time()
    
    try:
        # Your business logic
        user = create_user_logic(request.json)
        
        # Record success
        requests_total.labels(
            method='POST',
            endpoint='/users',
            status='201'
        ).inc()
        
        return jsonify(user), 201
        
    except Exception as e:
        # Record error
        requests_total.labels(
            method='POST',
            endpoint='/users',
            status='500'
        ).inc()
        raise
        
    finally:
        # Record duration
        duration = time.time() - start_time
        request_duration.labels(
            method='POST',
            endpoint='/users'
        ).observe(duration)
        
        active_requests.dec()
```

## Using Prometheus

### Access Prometheus UI

Open http://localhost:9090

### Useful Queries

#### Request Rate

```promql
# Requests per second by endpoint
rate(http_requests_total[5m])

# Requests per second for specific endpoint
rate(http_requests_total{endpoint="/users"}[5m])
```

#### Error Rate

```promql
# Error rate (percentage)
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100
```

#### Latency

```promql
# 95th percentile latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Average latency
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])
```

#### Service Health

```promql
# Success rate
sum(rate(http_requests_total{status=~"2.."}[5m])) / sum(rate(http_requests_total[5m])) * 100
```

## Practical Exercise

### Step 1: Generate Traffic

```bash
# Create some users
for i in {1..100}; do
  curl -X POST http://localhost:8080/users \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"User$i\", \"email\": \"user$i@example.com\"}"
done

# Create some orders
for i in {1..50}; do
  curl -X POST http://localhost:8080/orders \
    -H "Content-Type: application/json" \
    -d "{\"user_id\": \"$i\", \"product\": \"Product$i\", \"quantity\": 1}"
done
```

### Step 2: Explore Metrics in Prometheus

1. Open http://localhost:9090
2. Try these queries:

```promql
# Total requests
http_requests_total

# Request rate
rate(http_requests_total[1m])

# Error rate
rate(http_requests_total{status=~"5.."}[1m])

# P95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[1m]))
```

### Step 3: View in Grafana

1. Open http://localhost:3000 (admin/admin)
2. Go to Dashboards → Services Dashboard
3. See your metrics visualized!

## Creating Custom Metrics

Let's add a business metric:

```python
from prometheus_client import Counter

orders_total = Counter(
    'orders_total',
    'Total orders created',
    ['product_category']
)

@app.route('/orders', methods=['POST'])
def create_order():
    order = create_order_logic(request.json)
    
    # Increment business metric
    orders_total.labels(
        product_category=order.category
    ).inc()
    
    return jsonify(order), 201
```

Now you can track:
```promql
# Orders per second by category
rate(orders_total[5m])

# Most popular category
topk(3, sum by (product_category) (rate(orders_total[1h])))
```

## Alerting with Metrics

Define alerts in Prometheus:

```yaml
# prometheus/alerts.yml
groups:
  - name: service_alerts
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m])) 
          / sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"
      
      # High latency
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95, 
            rate(http_request_duration_seconds_bucket[5m])
          ) > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "P95 latency is {{ $value }}s"
```

## Metric Naming Conventions

Follow Prometheus naming conventions:

```
<namespace>_<subsystem>_<name>_<unit>
```

**Examples:**
```
http_requests_total          # Counter (use _total suffix)
http_request_duration_seconds # Histogram (include unit)
database_connections_active   # Gauge
process_cpu_seconds_total     # Counter with unit
```

## Common Metrics to Track

### Application Metrics

- Request rate
- Error rate
- Request duration
- Active connections
- Queue size

### Business Metrics

- Orders created
- Users registered
- Revenue generated
- Feature usage

### System Metrics

- CPU usage
- Memory usage
- Disk I/O
- Network traffic

## Key Takeaways

1. **Use the right metric type**: Counter, Gauge, Histogram, or Summary
2. **Follow the RED method**: Rate, Errors, Duration
3. **Keep labels low cardinality**: Avoid user IDs, timestamps
4. **Name metrics consistently**: Include units and follow conventions
5. **Track both technical and business metrics**
6. **Set up alerts** on important metrics

## What's Next?

Metrics show you *what* is happening. Next, we'll learn about distributed tracing, which shows you *where* and *why*.

Continue to [04-tracing.md](04-tracing.md) →

---

**Previous:** [02-logging.md](02-logging.md)
