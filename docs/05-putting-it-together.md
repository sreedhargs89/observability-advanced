# Putting It All Together

Now that you understand logs, metrics, and traces, let's see how they work together to solve real problems.

## The Three Pillars in Action

Each pillar answers different questions about the same issue:

| Pillar | Question | Example Answer |
|--------|----------|----------------|
| **Metrics** | "Is there a problem?" | "Error rate is 15% (normally 0.5%)" |
| **Traces** | "Where is the problem?" | "User service is timing out" |
| **Logs** | "Why is it happening?" | "Database connection pool exhausted" |

## Scenario 1: Debugging High Latency

### Step 1: Detect with Metrics

**Grafana Dashboard** shows:
```
P95 latency: 3.5s (normally 200ms) 🔴
```

**Prometheus Query:**
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

### Step 2: Locate with Traces

**Jaeger** shows a slow trace:
```
Total: 3.5s
├─ API Gateway: 50ms
└─ Order Service: 3.4s
   ├─ User Service: 3.2s ⚠️ SLOW!
   │  └─ Database Query: 3.1s
   └─ Inventory Check: 100ms
```

**Finding:** User Service database query is slow!

### Step 3: Diagnose with Logs

**Search logs** for that trace ID:
```bash
docker-compose logs | grep "trace_id=abc-123"
```

**Log entry:**
```json
{
  "level": "WARNING",
  "message": "Slow database query detected",
  "trace_id": "abc-123",
  "query": "SELECT * FROM users WHERE email LIKE '%@example.com'",
  "duration_ms": 3100,
  "rows_scanned": 1000000
}
```

**Root Cause:** Missing database index on email column!

### Step 4: Fix and Verify

```sql
CREATE INDEX idx_users_email ON users(email);
```

**Verify with metrics:**
```promql
# Latency back to normal
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
# Result: 180ms ✅
```

---

## Scenario 2: Investigating Errors

### Step 1: Alert from Metrics

**Alert fires:**
```
🚨 High Error Rate
Error rate: 12% (threshold: 5%)
Service: order-service
```

### Step 2: Find Failed Requests with Traces

**Jaeger search:**
- Service: order-service
- Tags: `error=true`

**Trace shows:**
```
POST /orders [500ms] ❌
├─ Validate Order [10ms] ✅
├─ Check User [50ms] ✅
└─ Process Payment [400ms] ❌ ERROR
   └─ Payment API Call [400ms] ❌
```

### Step 3: Examine Logs

**Filter logs:**
```bash
docker-compose logs order-service | grep ERROR
```

**Log shows:**
```json
{
  "level": "ERROR",
  "message": "Payment processing failed",
  "trace_id": "xyz-789",
  "error": "PaymentGatewayException: Card declined",
  "error_code": "CARD_DECLINED",
  "user_id": "12345"
}
```

**Root Cause:** Payment gateway rejecting cards (legitimate business error, not a bug)

### Step 4: Improve Observability

Add a metric to distinguish error types:

```python
payment_errors = Counter(
    'payment_errors_total',
    'Payment processing errors',
    ['error_type']
)

try:
    process_payment(card)
except CardDeclinedError as e:
    payment_errors.labels(error_type='card_declined').inc()
    # This is expected, don't alert
except PaymentGatewayError as e:
    payment_errors.labels(error_type='gateway_error').inc()
    # This is a real problem, alert!
```

---

## Scenario 3: Capacity Planning

### Use Metrics for Trends

**Track over time:**
```promql
# Request rate trend
rate(http_requests_total[1h])

# Memory usage trend
process_resident_memory_bytes

# Active connections trend
database_connections_active
```

**Create Grafana dashboard:**
- Request rate (last 30 days)
- Error rate (last 30 days)
- Latency percentiles (last 30 days)
- Resource usage (CPU, memory)

**Predict future needs:**
```promql
# Predict request rate in 30 days (linear regression)
predict_linear(rate(http_requests_total[7d])[30d:], 30*24*3600)
```

---

## Scenario 4: Debugging a Distributed Failure

### The Problem

Users can't create orders. Some succeed, some fail randomly.

### Step 1: Check Metrics

```promql
# Order service success rate
sum(rate(http_requests_total{service="order-service",status=~"2.."}[5m])) 
/ sum(rate(http_requests_total{service="order-service"}[5m]))
# Result: 60% (should be >99%)
```

### Step 2: Compare Traces

**Successful trace:**
```
POST /orders [200ms] ✅
├─ Order Service [150ms]
│  ├─ User Service [50ms] ✅
│  └─ Inventory Service [80ms] ✅
└─ Response [10ms]
```

**Failed trace:**
```
POST /orders [5000ms] ❌ TIMEOUT
├─ Order Service [4900ms]
│  ├─ User Service [4800ms] ❌ TIMEOUT
│  │  └─ (no child spans - request never completed)
│  └─ (inventory check never started)
└─ Error Response [100ms]
```

**Pattern:** User Service timeouts cause order failures

### Step 3: Check User Service Logs

```bash
docker-compose logs user-service | grep -A 5 "ERROR"
```

**Logs show:**
```json
{
  "level": "ERROR",
  "message": "Database connection timeout",
  "error": "could not connect to server: Connection refused",
  "db_host": "postgres-replica-2",
  "timestamp": "2025-11-21T00:15:23Z"
}
```

### Step 4: Check Infrastructure

**Metrics show:**
```promql
database_connections_active{instance="postgres-replica-2"}
# Result: 0 (other replicas: 50)
```

**Root Cause:** postgres-replica-2 is down!

### Step 5: Fix and Verify

```bash
# Restart failed replica
docker-compose restart postgres-replica-2
```

**Verify:**
```promql
# Success rate back to normal
sum(rate(http_requests_total{service="order-service",status=~"2.."}[5m])) 
/ sum(rate(http_requests_total{service="order-service"}[5m]))
# Result: 99.8% ✅
```

---

## Best Practices for Production

### 1. Set Up Alerts

**Good alerts:**
```yaml
# High error rate
- alert: HighErrorRate
  expr: |
    sum(rate(http_requests_total{status=~"5.."}[5m])) 
    / sum(rate(http_requests_total[5m])) > 0.01
  for: 5m

# High latency
- alert: HighLatency
  expr: |
    histogram_quantile(0.95, 
      rate(http_request_duration_seconds_bucket[5m])
    ) > 1.0
  for: 5m

# Service down
- alert: ServiceDown
  expr: up{job="user-service"} == 0
  for: 1m
```

### 2. Create Useful Dashboards

**Service Health Dashboard:**
- Request rate (last 24h)
- Error rate (last 24h)
- P50, P95, P99 latency
- Success rate
- Active instances

**Business Metrics Dashboard:**
- Orders per hour
- Revenue per hour
- New users per hour
- Conversion rate

### 3. Implement SLOs

**Service Level Objectives:**

```yaml
# Availability SLO: 99.9%
availability_slo: 0.999

# Latency SLO: 95% of requests < 500ms
latency_slo_p95: 0.5

# Error budget
error_budget: 0.001  # 0.1% of requests can fail
```

**Track SLO compliance:**
```promql
# Availability (last 30 days)
sum(rate(http_requests_total{status=~"2.."}[30d])) 
/ sum(rate(http_requests_total[30d]))

# Error budget remaining
1 - (
  sum(rate(http_requests_total{status=~"5.."}[30d])) 
  / sum(rate(http_requests_total[30d]))
) / 0.001
```

### 4. Correlation Between Pillars

**Always connect the three pillars:**

```python
import logging
from opentelemetry import trace

# Get current trace context
span = trace.get_current_span()
trace_id = span.get_span_context().trace_id

# Include trace ID in logs
logger.info("Processing order", extra={
    "trace_id": format(trace_id, '032x'),
    "order_id": order.id
})

# Include trace ID in metrics
order_processing_duration.labels(
    trace_id=format(trace_id, '032x')[:8]  # First 8 chars
).observe(duration)
```

### 5. Runbook Integration

**Link alerts to runbooks:**

```yaml
- alert: HighErrorRate
  annotations:
    summary: "High error rate detected"
    description: "Error rate is {{ $value | humanizePercentage }}"
    runbook_url: "https://wiki.example.com/runbooks/high-error-rate"
    dashboard_url: "https://grafana.example.com/d/service-health"
    jaeger_url: "https://jaeger.example.com/search?service=order-service&tags=error:true"
```

---

## Hands-On Exercise

Let's practice using all three pillars together!

### Exercise: Debug a Performance Issue

We've added a simulated performance issue to the order service.

#### Step 1: Generate Traffic

```bash
# Create 20 orders
for i in {1..20}; do
  curl -X POST http://localhost:8080/orders \
    -H "Content-Type: application/json" \
    -d "{\"user_id\": \"$i\", \"product\": \"Product$i\", \"quantity\": 1}"
  sleep 0.5
done
```

#### Step 2: Check Metrics

1. Open Grafana: http://localhost:3000
2. Go to Services Dashboard
3. Look for anomalies in:
   - Request rate
   - Error rate
   - Latency

**Question:** What do you notice?

#### Step 3: Find Slow Traces

1. Open Jaeger: http://localhost:16686
2. Select "order-service"
3. Set "Min Duration" to find slow requests
4. Click on a slow trace

**Question:** Which span is taking the most time?

#### Step 4: Examine Logs

```bash
# Find logs for a specific trace
docker-compose logs | grep "trace_id=<YOUR_TRACE_ID>"
```

**Question:** What do the logs tell you?

#### Step 5: Form a Hypothesis

Based on metrics, traces, and logs:
- What is the root cause?
- How would you fix it?
- How would you prevent it in the future?

---

## Observability Maturity Model

### Level 1: Basic Monitoring
- ✅ Health checks
- ✅ Uptime monitoring
- ✅ Basic logs

### Level 2: Instrumented
- ✅ Structured logging
- ✅ Basic metrics (request count, errors)
- ✅ Simple dashboards

### Level 3: Observable
- ✅ Distributed tracing
- ✅ Rich metrics (RED method)
- ✅ Correlation IDs
- ✅ Useful dashboards

### Level 4: Proactive
- ✅ SLOs and error budgets
- ✅ Automated alerts
- ✅ Anomaly detection
- ✅ Capacity planning

### Level 5: Optimized
- ✅ Continuous improvement
- ✅ Cost optimization
- ✅ Advanced analytics
- ✅ Predictive alerting

**Where are you now? Where do you want to be?**

---

## Key Takeaways

1. **Use all three pillars together** - They complement each other
2. **Metrics detect** problems, **traces locate** them, **logs explain** them
3. **Correlation is key** - Connect logs, metrics, and traces with IDs
4. **Automate alerting** - Don't wait for users to report issues
5. **Create useful dashboards** - Make data actionable
6. **Practice debugging** - The more you use these tools, the better you get

## Next Steps

### Continue Learning
- Explore advanced Prometheus queries (PromQL)
- Learn Grafana alerting
- Study OpenTelemetry in depth
- Read about SRE practices

### Improve This Project
- Add more services
- Implement authentication
- Add database tracing
- Create custom metrics
- Build more dashboards

### Apply to Your Work
- Instrument your services
- Set up observability stack
- Define SLOs
- Create runbooks
- Train your team

---

## Additional Resources

### Documentation
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Grafana Tutorials](https://grafana.com/tutorials/)

### Books
- "Observability Engineering" by Charity Majors
- "Site Reliability Engineering" by Google
- "Distributed Systems Observability" by Cindy Sridharan

### Communities
- [CNCF Slack](https://slack.cncf.io/) - #observability channel
- [OpenTelemetry Community](https://opentelemetry.io/community/)
- [Prometheus Community](https://prometheus.io/community/)

---

**Congratulations!** 🎉

You've completed the observability tutorial! You now understand:
- ✅ The three pillars of observability
- ✅ How to implement logging, metrics, and tracing
- ✅ How to use Prometheus, Jaeger, and Grafana
- ✅ How to debug distributed systems
- ✅ Best practices for production

**Keep learning, keep observing!** 🚀

---

**Previous:** [04-tracing.md](04-tracing.md)
