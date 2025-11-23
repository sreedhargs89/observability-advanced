# Logging Deep Dive

Logging is the foundation of observability. Good logs tell the story of what your application is doing.

## Structured vs Unstructured Logging

### Unstructured Logging ❌

```python
print("User alice@example.com created order 123 for $99.99")
```

**Problems:**
- Hard to parse programmatically
- Difficult to search and filter
- No consistent format
- Can't aggregate or analyze

### Structured Logging ✅

```python
logger.info("Order created", extra={
    "event": "order_created",
    "user_email": "alice@example.com",
    "order_id": 123,
    "amount": 99.99,
    "currency": "USD"
})
```

**Output (JSON):**
```json
{
  "timestamp": "2025-11-21T00:00:00Z",
  "level": "INFO",
  "message": "Order created",
  "event": "order_created",
  "user_email": "alice@example.com",
  "order_id": 123,
  "amount": 99.99,
  "currency": "USD",
  "service": "order-service",
  "trace_id": "abc123"
}
```

**Benefits:**
- ✅ Easy to search: `event="order_created" AND amount > 50`
- ✅ Aggregatable: "How many orders created today?"
- ✅ Consistent format across services
- ✅ Machine-readable

## Log Levels

Use the right level for the right situation:

| Level | When to Use | Example |
|-------|-------------|---------|
| **DEBUG** | Detailed diagnostic info | "SQL query: SELECT * FROM users WHERE id=123" |
| **INFO** | General informational events | "User logged in successfully" |
| **WARNING** | Something unexpected but handled | "API rate limit approaching (80% used)" |
| **ERROR** | Error that affects functionality | "Failed to save order to database" |
| **CRITICAL** | System-level failures | "Database connection pool exhausted" |

### Examples from Our Services

```python
# DEBUG - Development/troubleshooting
logger.debug("Validating user input", extra={"input": user_data})

# INFO - Normal operations
logger.info("User created", extra={"user_id": user.id})

# WARNING - Potential issues
logger.warning("Slow database query", extra={
    "query_time_ms": 1500,
    "threshold_ms": 1000
})

# ERROR - Actual problems
logger.error("Failed to process payment", extra={
    "order_id": order.id,
    "error": str(e)
})

# CRITICAL - System failures
logger.critical("Cannot connect to database", extra={
    "host": db_host,
    "error": str(e)
})
```

## Best Practices

### 1. Include Context

```python
# ❌ Not enough context
logger.error("Save failed")

# ✅ Rich context
logger.error("Failed to save user to database", extra={
    "user_id": user.id,
    "operation": "create_user",
    "error": str(e),
    "retry_count": retry_count
})
```

### 2. Use Correlation IDs

Link related logs across services:

```python
# Generate or extract correlation ID
correlation_id = request.headers.get('X-Correlation-ID') or str(uuid.uuid4())

# Include in all logs
logger.info("Processing request", extra={
    "correlation_id": correlation_id,
    "endpoint": request.path
})

# Pass to downstream services
response = requests.post(url, 
    headers={"X-Correlation-ID": correlation_id},
    json=data
)
```

### 3. Log at Service Boundaries

Always log when entering/exiting your service:

```python
@app.route('/users', methods=['POST'])
def create_user():
    correlation_id = request.headers.get('X-Correlation-ID', str(uuid.uuid4()))
    
    # Log incoming request
    logger.info("Received create user request", extra={
        "correlation_id": correlation_id,
        "endpoint": "/users",
        "method": "POST"
    })
    
    try:
        user = create_user_logic(request.json)
        
        # Log successful response
        logger.info("User created successfully", extra={
            "correlation_id": correlation_id,
            "user_id": user.id
        })
        
        return jsonify(user), 201
        
    except Exception as e:
        # Log errors
        logger.error("Failed to create user", extra={
            "correlation_id": correlation_id,
            "error": str(e)
        })
        raise
```

### 4. Don't Log Sensitive Data

```python
# ❌ Logging sensitive data
logger.info("User login", extra={
    "email": user.email,
    "password": user.password  # NEVER!
})

# ✅ Redact or omit sensitive fields
logger.info("User login", extra={
    "email": user.email,
    "user_id": user.id
})
```

### 5. Use Consistent Field Names

Create a standard across your organization:

```python
# Standard fields
STANDARD_FIELDS = {
    "user_id": "user_id",      # Not "userId" or "user"
    "order_id": "order_id",    # Not "orderId" or "id"
    "trace_id": "trace_id",    # Not "traceId" or "trace"
}
```

## Viewing Logs in Our Tutorial

### View Logs from a Specific Service

```bash
# User service logs
docker-compose logs -f user-service

# Order service logs
docker-compose logs -f order-service

# API gateway logs
docker-compose logs -f api-gateway
```

### Follow All Logs

```bash
docker-compose logs -f
```

### Search Logs

```bash
# Find all ERROR logs
docker-compose logs | grep ERROR

# Find logs for a specific correlation ID
docker-compose logs | grep "abc-123-def"

# Find logs for a specific user
docker-compose logs | grep "user_id.*12345"
```

## Practical Exercise

Let's trace a request through our system using logs:

### Step 1: Create an Order

```bash
curl -X POST http://localhost:8080/orders \
  -H "Content-Type: application/json" \
  -H "X-Correlation-ID: exercise-001" \
  -d '{
    "user_id": "1",
    "product": "Laptop",
    "quantity": 1
  }'
```

### Step 2: Find Related Logs

```bash
docker-compose logs | grep "exercise-001"
```

You should see logs from:
1. **API Gateway** - Received request
2. **Order Service** - Processing order
3. **User Service** - Validating user
4. **Order Service** - Order created
5. **API Gateway** - Returning response

### Step 3: Analyze the Flow

Notice how the correlation ID ties everything together!

## Log Aggregation

In production, you'd use log aggregation tools:

- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Grafana Loki**
- **Splunk**
- **Datadog**
- **CloudWatch Logs** (AWS)

These tools let you:
- Search across all services
- Create dashboards
- Set up alerts
- Analyze patterns

## Common Logging Patterns

### 1. Request/Response Logging

```python
@app.before_request
def log_request():
    logger.info("Incoming request", extra={
        "method": request.method,
        "path": request.path,
        "correlation_id": g.correlation_id
    })

@app.after_request
def log_response(response):
    logger.info("Outgoing response", extra={
        "status_code": response.status_code,
        "correlation_id": g.correlation_id
    })
    return response
```

### 2. Error Logging with Stack Traces

```python
try:
    result = risky_operation()
except Exception as e:
    logger.error("Operation failed", extra={
        "operation": "risky_operation",
        "error": str(e),
        "error_type": type(e).__name__
    }, exc_info=True)  # Includes stack trace
    raise
```

### 3. Performance Logging

```python
import time

start_time = time.time()
result = slow_operation()
duration_ms = (time.time() - start_time) * 1000

logger.info("Operation completed", extra={
    "operation": "slow_operation",
    "duration_ms": duration_ms
})

if duration_ms > 1000:
    logger.warning("Slow operation detected", extra={
        "operation": "slow_operation",
        "duration_ms": duration_ms,
        "threshold_ms": 1000
    })
```

## What to Log

### ✅ DO Log

- Service startup/shutdown
- Incoming requests
- Outgoing requests to other services
- Business events (order created, user registered)
- Errors and exceptions
- Performance warnings
- Configuration changes

### ❌ DON'T Log

- Passwords or secrets
- Credit card numbers
- Personal identifiable information (PII) without redaction
- Excessive debug info in production
- Every single database query (use sampling)

## Log Retention

Consider how long to keep logs:

| Type | Retention | Reason |
|------|-----------|--------|
| **DEBUG** | 1-7 days | High volume, low value |
| **INFO** | 30-90 days | Useful for analysis |
| **WARNING** | 90-180 days | Trend analysis |
| **ERROR** | 1 year | Compliance, debugging |
| **CRITICAL** | 1+ years | Incident investigation |

## Key Takeaways

1. **Use structured logging** (JSON format)
2. **Include correlation IDs** to trace requests
3. **Log at appropriate levels** (DEBUG, INFO, WARNING, ERROR, CRITICAL)
4. **Add rich context** to every log
5. **Never log sensitive data**
6. **Be consistent** with field names
7. **Log at service boundaries**

## What's Next?

Logs tell you *what happened*. Next, we'll learn about metrics, which tell you *how much* and *how often*.

Continue to [03-metrics.md](03-metrics.md) →

---

**Previous:** [01-introduction.md](01-introduction.md)
