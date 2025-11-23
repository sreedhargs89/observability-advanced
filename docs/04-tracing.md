# Distributed Tracing

Distributed tracing shows you how requests flow through your microservices. It's essential for debugging distributed systems.

## What is a Trace?

A **trace** represents the complete journey of a request through your system.

### Example: Creating an Order

```
User Request → API Gateway → Order Service → User Service → Database
```

Without tracing, you'd need to:
1. Check API Gateway logs
2. Find the correlation ID
3. Search Order Service logs
4. Search User Service logs
5. Piece everything together manually

With tracing, you see the entire flow in one view!

## Key Concepts

### 1. Trace

The complete journey of a request.

**Trace ID:** `abc-123-def` (unique identifier)

### 2. Span

A single operation within a trace.

**Example Spans:**
- "HTTP GET /orders"
- "Database query: SELECT * FROM users"
- "Call to payment service"

### 3. Parent-Child Relationships

Spans form a tree structure:

```
Trace: abc-123-def
│
├─ Span: API Gateway [100ms]
   │
   ├─ Span: Order Service [80ms]
      │
      ├─ Span: User Service [30ms]
      │  └─ Span: DB Query [20ms]
      │
      └─ Span: Inventory Service [40ms]
         └─ Span: DB Query [25ms]
```

### 4. Span Attributes

Metadata attached to spans:

```python
{
    "http.method": "POST",
    "http.url": "/orders",
    "http.status_code": 201,
    "user.id": "12345",
    "order.id": "67890"
}
```

### 5. Context Propagation

Passing trace context between services:

```
Service A → Service B
   │           │
   └─ Headers ─┘
      Trace-ID: abc-123
      Span-ID: span-456
```

## OpenTelemetry

We use **OpenTelemetry** (OTel) for instrumentation. It's the industry standard for observability.

### Basic Setup

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor

# Create tracer provider
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Configure Jaeger exporter
jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger",
    agent_port=6831,
)

# Add span processor
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

# Auto-instrument Flask
FlaskInstrumentor().instrument_app(app)
```

### Creating Spans

#### Automatic Instrumentation

OpenTelemetry automatically creates spans for:
- HTTP requests (Flask, requests library)
- Database queries (SQLAlchemy, psycopg2)
- Redis operations
- And more!

```python
# This automatically creates a span!
@app.route('/users/<user_id>')
def get_user(user_id):
    return jsonify(fetch_user(user_id))
```

#### Manual Spans

For custom operations:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@app.route('/orders', methods=['POST'])
def create_order():
    # Create a custom span
    with tracer.start_as_current_span("create_order") as span:
        # Add attributes
        span.set_attribute("order.product", request.json['product'])
        span.set_attribute("order.quantity", request.json['quantity'])
        
        # Your business logic
        order = process_order(request.json)
        
        # Add more attributes
        span.set_attribute("order.id", order.id)
        span.set_attribute("order.total", order.total)
        
        return jsonify(order), 201
```

#### Nested Spans

```python
with tracer.start_as_current_span("process_order") as parent_span:
    parent_span.set_attribute("order.id", order_id)
    
    # Child span 1
    with tracer.start_as_current_span("validate_inventory"):
        check_inventory(order.items)
    
    # Child span 2
    with tracer.start_as_current_span("calculate_total"):
        total = calculate_total(order.items)
    
    # Child span 3
    with tracer.start_as_current_span("save_to_database"):
        db.save(order)
```

### Adding Events

Events are timestamped logs within a span:

```python
with tracer.start_as_current_span("process_payment") as span:
    span.add_event("Payment validation started")
    
    validate_payment_info(payment_data)
    span.add_event("Payment validation completed")
    
    charge_payment(payment_data)
    span.add_event("Payment charged successfully", {
        "amount": payment_data.amount,
        "currency": payment_data.currency
    })
```

### Recording Errors

```python
from opentelemetry.trace import Status, StatusCode

with tracer.start_as_current_span("risky_operation") as span:
    try:
        result = risky_operation()
    except Exception as e:
        # Record the exception
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR, str(e)))
        raise
```

## Context Propagation

The magic that connects spans across services!

### How It Works

1. **Service A** creates a trace
2. **Service A** injects trace context into HTTP headers
3. **Service B** extracts trace context from headers
4. **Service B** creates child spans with the same trace ID

### Automatic Propagation

OpenTelemetry handles this automatically:

```python
# Service A (Order Service)
import requests

# Trace context automatically injected into headers!
response = requests.get('http://user-service:8001/users/123')
```

### Manual Propagation (if needed)

```python
from opentelemetry.propagate import inject, extract

# Inject context into headers
headers = {}
inject(headers)

# Make request with headers
response = requests.get(url, headers=headers)

# Extract context from incoming headers
context = extract(request.headers)
```

## Using Jaeger UI

### Access Jaeger

Open http://localhost:16686

### Finding Traces

1. **Select Service**: Choose "api-gateway", "user-service", or "order-service"
2. **Set Time Range**: Last hour, last 15 minutes, etc.
3. **Add Filters**: 
   - Min duration: Find slow requests
   - Tags: `http.status_code=500` for errors
4. **Click "Find Traces"**

### Understanding the Trace View

```
┌─────────────────────────────────────────────────┐
│ Trace: abc-123-def                              │
│ Duration: 245ms                                 │
│ Services: 3    Spans: 7                         │
├─────────────────────────────────────────────────┤
│ ▼ api-gateway: POST /orders [245ms]            │
│   ├─ order-service: create_order [200ms]       │
│   │  ├─ order-service: validate_order [20ms]   │
│   │  ├─ user-service: GET /users/123 [50ms]    │
│   │  │  └─ user-service: db_query [30ms]       │
│   │  ├─ order-service: calculate_total [10ms]  │
│   │  └─ order-service: save_order [100ms]      │
│   │     └─ order-service: db_insert [90ms]     │
│   └─ api-gateway: format_response [15ms]       │
└─────────────────────────────────────────────────┘
```

**Key Information:**
- **Timeline**: Visual representation of when each span occurred
- **Duration**: How long each operation took
- **Service**: Which service handled each span
- **Tags**: Metadata (HTTP method, status code, etc.)
- **Logs**: Events within the span

## Practical Exercise

### Step 1: Generate a Trace

```bash
curl -X POST http://localhost:8080/orders \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "1",
    "product": "Laptop",
    "quantity": 1
  }'
```

### Step 2: Find the Trace in Jaeger

1. Open http://localhost:16686
2. Select "api-gateway" service
3. Click "Find Traces"
4. Click on the most recent trace

### Step 3: Analyze the Trace

Look for:
- **Total duration**: How long did the request take?
- **Service breakdown**: Which service took the most time?
- **Span details**: Click on spans to see attributes
- **Timeline gaps**: Any delays between spans?

### Step 4: Simulate a Slow Request

```bash
# Add a delay parameter (if implemented)
curl -X POST http://localhost:8080/orders?delay=2000 \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "1",
    "product": "Laptop",
    "quantity": 1
  }'
```

Find this trace in Jaeger and see which span is slow!

## Common Tracing Patterns

### 1. Database Queries

```python
with tracer.start_as_current_span("database_query") as span:
    span.set_attribute("db.system", "postgresql")
    span.set_attribute("db.statement", "SELECT * FROM users WHERE id = ?")
    span.set_attribute("db.user", "app_user")
    
    result = db.execute(query)
    
    span.set_attribute("db.rows_affected", len(result))
```

### 2. External API Calls

```python
with tracer.start_as_current_span("external_api_call") as span:
    span.set_attribute("http.method", "GET")
    span.set_attribute("http.url", "https://api.example.com/data")
    
    response = requests.get("https://api.example.com/data")
    
    span.set_attribute("http.status_code", response.status_code)
    span.set_attribute("http.response_size", len(response.content))
```

### 3. Background Jobs

```python
# Start a new trace for background job
with tracer.start_as_current_span("process_background_job") as span:
    span.set_attribute("job.type", "email_notification")
    span.set_attribute("job.id", job_id)
    
    process_job(job_id)
```

### 4. Batch Operations

```python
with tracer.start_as_current_span("batch_process") as span:
    span.set_attribute("batch.size", len(items))
    
    for i, item in enumerate(items):
        with tracer.start_as_current_span(f"process_item_{i}") as item_span:
            item_span.set_attribute("item.id", item.id)
            process_item(item)
    
    span.set_attribute("batch.processed", len(items))
```

## Sampling

In production, tracing every request is expensive. Use sampling:

### Probability Sampling

```python
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

# Sample 10% of requests
sampler = TraceIdRatioBased(0.1)
```

### Parent-Based Sampling

```python
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

# If parent is sampled, sample child. Otherwise, use 10% sampling
sampler = ParentBased(root=TraceIdRatioBased(0.1))
```

### Custom Sampling

```python
class CustomSampler:
    def should_sample(self, context, trace_id, name, attributes):
        # Always sample errors
        if attributes.get("http.status_code", 0) >= 500:
            return Decision.RECORD_AND_SAMPLE
        
        # Sample 1% of successful requests
        if random.random() < 0.01:
            return Decision.RECORD_AND_SAMPLE
        
        return Decision.DROP
```

## Debugging with Traces

### Finding Slow Requests

1. Go to Jaeger UI
2. Set "Min Duration" to 1s
3. Find traces taking longer than expected
4. Identify the slowest span
5. Optimize that operation

### Finding Errors

1. Search with tag: `error=true`
2. Or: `http.status_code=500`
3. Look at span events and exceptions
4. Trace back to the root cause

### Understanding Dependencies

1. View the trace timeline
2. See which services call which
3. Identify critical paths
4. Find unnecessary calls

## Best Practices

### ✅ DO

- **Name spans clearly**: "fetch_user", not "operation"
- **Add meaningful attributes**: user_id, order_id, etc.
- **Record exceptions**: Use `span.record_exception(e)`
- **Use semantic conventions**: Follow OpenTelemetry standards
- **Sample in production**: Don't trace everything

### ❌ DON'T

- **Create too many spans**: Adds overhead
- **Add sensitive data**: No passwords, tokens
- **Ignore errors**: Always record exceptions
- **Use high cardinality attributes**: No unique IDs in span names

## Semantic Conventions

Follow OpenTelemetry semantic conventions:

### HTTP Spans

```python
span.set_attribute("http.method", "POST")
span.set_attribute("http.url", "/api/orders")
span.set_attribute("http.status_code", 201)
span.set_attribute("http.user_agent", request.headers.get("User-Agent"))
```

### Database Spans

```python
span.set_attribute("db.system", "postgresql")
span.set_attribute("db.name", "orders_db")
span.set_attribute("db.statement", "INSERT INTO orders ...")
span.set_attribute("db.operation", "INSERT")
```

### RPC Spans

```python
span.set_attribute("rpc.system", "grpc")
span.set_attribute("rpc.service", "UserService")
span.set_attribute("rpc.method", "GetUser")
```

## Key Takeaways

1. **Traces show request flows** across distributed services
2. **Spans represent operations** within a trace
3. **Context propagation** connects spans across services
4. **OpenTelemetry** is the standard for instrumentation
5. **Jaeger UI** helps visualize and debug traces
6. **Use sampling** in production to reduce overhead
7. **Follow semantic conventions** for consistency

## What's Next?

You've learned all three pillars! Now let's put them together.

Continue to [05-putting-it-together.md](05-putting-it-together.md) →

---

**Previous:** [03-metrics.md](03-metrics.md)
