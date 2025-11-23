# OpenTelemetry: The Complete Guide

## Table of Contents
1. [What is OpenTelemetry?](#1-what-is-opentelemetry)
2. [Why OpenTelemetry is Needed](#2-why-opentelemetry-is-needed)
3. [The Problem Before OpenTelemetry](#3-the-problem-before-opentelemetry)
4. [OpenTelemetry Architecture](#4-opentelemetry-architecture)
5. [How We Use OpenTelemetry in This Project](#5-how-we-use-opentelemetry-in-this-project)
6. [Practical Implementation Examples](#6-practical-implementation-examples)
7. [Advanced Features](#7-advanced-features)
8. [Best Practices](#8-best-practices)

---

## 1. What is OpenTelemetry?

**OpenTelemetry (OTel)** is an open-source observability framework that provides a **single, vendor-neutral way** to collect, process, and export telemetry data (metrics, logs, and traces) from your applications.

### Key Points:
- **Industry Standard**: Backed by CNCF (Cloud Native Computing Foundation)
- **Vendor-Neutral**: Works with any observability backend (Jaeger, Prometheus, Datadog, New Relic, etc.)
- **Unified API**: One library for all three pillars of observability
- **Language Support**: Available in 11+ programming languages

### The Three Pillars OpenTelemetry Supports:

```
┌─────────────────────────────────────────┐
│         OpenTelemetry SDK               │
├─────────────────────────────────────────┤
│  📝 Traces  │  📊 Metrics  │  📄 Logs   │
├─────────────────────────────────────────┤
│         Exporters (OTLP, Jaeger, etc.)  │
└─────────────────────────────────────────┘
           │
           ▼
    ┌──────────────┐
    │   Backends   │
    │ (Jaeger,     │
    │  Prometheus, │
    │  Loki, etc.) │
    └──────────────┘
```

---

## 2. Why OpenTelemetry is Needed

### 2.1 The Vendor Lock-In Problem

**Before OpenTelemetry:**

Imagine you're using Datadog for observability:

```python
# Datadog-specific code
from ddtrace import tracer

@tracer.wrap()
def my_function():
    pass
```

**Problem:** If you want to switch to New Relic or Jaeger, you have to:
1. Rewrite all your instrumentation code
2. Change all imports
3. Redeploy everything
4. Risk breaking production

**With OpenTelemetry:**

```python
# Vendor-neutral code
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("my_function")
def my_function():
    pass
```

**Benefit:** Switch backends by just changing the exporter configuration. **No code changes needed!**

### 2.2 The Fragmentation Problem

**Before OpenTelemetry**, each vendor had their own SDK:

| Vendor | Tracing Library | Metrics Library | Logs Library |
|--------|----------------|-----------------|--------------|
| Jaeger | `jaeger-client` | - | - |
| Zipkin | `py_zipkin` | - | - |
| Prometheus | - | `prometheus-client` | - |
| Datadog | `ddtrace` | `datadog` | `datadog` |
| New Relic | `newrelic` | `newrelic` | `newrelic` |

**Problems:**
- Learn different APIs for each vendor
- Maintain multiple SDKs
- Inconsistent data formats
- Hard to switch vendors

**With OpenTelemetry:**

```
┌────────────────────────────────┐
│   OpenTelemetry SDK (One API)  │
└────────────────────────────────┘
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
 Jaeger   Datadog   New Relic
```

**One SDK, multiple backends!**

### 2.3 The Standardization Problem

**Example:** How do you represent an HTTP request?

**Before OpenTelemetry (Chaos):**
```python
# Vendor A
span.set_tag("http.method", "GET")
span.set_tag("http.url", "/users")

# Vendor B
span.add_attribute("method", "GET")
span.add_attribute("path", "/users")

# Vendor C
span.log("request_method", "GET")
span.log("request_path", "/users")
```

**With OpenTelemetry (Standard):**
```python
# Everyone uses the same semantic conventions
span.set_attribute("http.method", "GET")
span.set_attribute("http.url", "/users")
span.set_attribute("http.status_code", 200)
```

**Benefit:** Consistent data across all tools and vendors.

---

## 3. The Problem Before OpenTelemetry

### 3.1 Real-World Scenario

Let's say you're a company using:
- **Jaeger** for tracing
- **Prometheus** for metrics
- **ELK** for logs

Your code looks like this:

```python
# Three different SDKs!
from jaeger_client import Config as JaegerConfig
from prometheus_client import Counter, Histogram
import logging

# Jaeger setup
jaeger_config = JaegerConfig(...)
tracer = jaeger_config.initialize_tracer()

# Prometheus setup
request_counter = Counter('requests_total', 'Total requests')
request_duration = Histogram('request_duration', 'Request duration')

# Logging setup
logger = logging.getLogger(__name__)

@app.route('/users')
def get_users():
    # Start Jaeger span
    with tracer.start_span('get_users') as span:
        # Increment Prometheus counter
        request_counter.inc()
        
        # Log event
        logger.info("Fetching users")
        
        # Your business logic
        users = fetch_users()
        
        # Record Prometheus metric
        request_duration.observe(0.5)
        
        return users
```

**Problems:**
1. **Three different APIs** to learn and maintain
2. **No correlation** between traces, metrics, and logs
3. **Vendor lock-in** - switching is painful
4. **Inconsistent data** - each tool uses different formats

### 3.2 The Migration Nightmare

**Scenario:** Your company decides to switch from Jaeger to Datadog.

**What you have to do:**
1. Remove `jaeger-client` dependency
2. Add `ddtrace` dependency
3. Find and replace all `tracer.start_span()` calls
4. Change all `span.set_tag()` to `span.set_tag()` (different API!)
5. Update configuration
6. Test everything
7. Deploy to production (risky!)

**Time:** Weeks or months  
**Risk:** High (breaking production)  
**Cost:** Expensive (developer time, potential downtime)

---

## 4. OpenTelemetry Architecture

### 4.1 Components

```
┌─────────────────────────────────────────────────────┐
│              Your Application                        │
├─────────────────────────────────────────────────────┤
│  OpenTelemetry API (What you code against)          │
│  - trace.get_tracer()                               │
│  - metrics.get_meter()                              │
│  - logs.get_logger()                                │
├─────────────────────────────────────────────────────┤
│  OpenTelemetry SDK (Implementation)                 │
│  - TracerProvider                                   │
│  - MeterProvider                                    │
│  - LoggerProvider                                   │
├─────────────────────────────────────────────────────┤
│  Instrumentation Libraries (Auto-instrumentation)   │
│  - Flask, Django, FastAPI                          │
│  - Requests, HTTPX                                  │
│  - SQLAlchemy, psycopg2                            │
├─────────────────────────────────────────────────────┤
│  Processors (Transform data)                        │
│  - BatchSpanProcessor                               │
│  - SimpleSpanProcessor                              │
├─────────────────────────────────────────────────────┤
│  Exporters (Send data to backends)                  │
│  - OTLP (OpenTelemetry Protocol)                   │
│  - Jaeger                                           │
│  - Prometheus                                       │
│  - Zipkin                                           │
└─────────────────────────────────────────────────────┘
           │
           ▼
    ┌──────────────┐
    │   Backends   │
    │ (Jaeger,     │
    │  Prometheus, │
    │  Grafana)    │
    └──────────────┘
```

### 4.2 Key Concepts

#### API vs SDK

**API (What you code against):**
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("my_operation"):
    # Your code
    pass
```

**SDK (Implementation):**
```python
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Configure the SDK
trace.set_tracer_provider(TracerProvider())
exporter = OTLPSpanExporter(endpoint="http://jaeger:4317")
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(exporter))
```

**Why separate?**
- **API**: Stable, rarely changes, what you code against
- **SDK**: Can be swapped, configured, or replaced without changing your code

#### Instrumentation Libraries

**Auto-instrumentation** means OpenTelemetry automatically creates spans for common operations:

```python
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# Automatically instrument Flask
FlaskInstrumentor().instrument_app(app)

# Automatically instrument requests library
RequestsInstrumentor().instrument()

# Now every Flask route and requests call automatically creates spans!
@app.route('/users')
def get_users():
    # This automatically creates a span!
    response = requests.get('http://api.example.com/users')
    # This also automatically creates a span!
    return response.json()
```

**No manual span creation needed!**

---

## 5. How We Use OpenTelemetry in This Project

### 5.1 Project Setup Overview

In our observability tutorial, we use OpenTelemetry to:
1. **Trace** requests across API Gateway → Order Service → User Service
2. **Collect metrics** (request count, duration, errors)
3. **Correlate logs** with traces using trace IDs

### 5.2 Installation

**In each service's `requirements.txt`:**
```txt
# Core OpenTelemetry
opentelemetry-api==1.21.0
opentelemetry-sdk==1.21.0

# Auto-instrumentation for Flask
opentelemetry-instrumentation-flask==0.42b0

# Auto-instrumentation for requests library
opentelemetry-instrumentation-requests==0.42b0

# Exporter (OTLP protocol to send to Jaeger)
opentelemetry-exporter-otlp==1.21.0
```

### 5.3 Complete Setup (Step-by-Step)

**File: `api-gateway/app.py`**

```python
# Step 1: Import OpenTelemetry components
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# Step 2: Define service identity
resource = Resource(attributes={
    "service.name": "api-gateway",  # This appears in Jaeger UI
    "service.version": "1.0.0",
    "deployment.environment": "development"
})

# Step 3: Create and configure the tracer provider
trace.set_tracer_provider(TracerProvider(resource=resource))

# Step 4: Get a tracer instance
tracer = trace.get_tracer(__name__)

# Step 5: Configure the exporter (where to send traces)
otlp_exporter = OTLPSpanExporter(
    endpoint="http://jaeger:4317",  # Jaeger's OTLP receiver
    insecure=True  # No TLS for local development
)

# Step 6: Add a span processor (batches spans before sending)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(otlp_exporter)
)

# Step 7: Auto-instrument Flask (creates spans for all routes)
FlaskInstrumentor().instrument_app(app)

# Step 8: Auto-instrument requests library (creates spans for HTTP calls)
RequestsInstrumentor().instrument()
```

**That's it!** Now every HTTP request and outgoing call is automatically traced.

### 5.4 How It Works in Practice

#### Automatic Tracing

```python
@app.route('/orders', methods=['POST'])
def create_order():
    # OpenTelemetry automatically creates a span for this route!
    # Span name: "POST /orders"
    # Span attributes: http.method, http.url, http.status_code
    
    data = request.get_json()
    
    # This HTTP call also automatically creates a span!
    # Span name: "HTTP POST"
    # Parent: The route span above
    response = requests.post(
        'http://order-service:8002/orders',
        json=data
    )
    
    return response.json(), response.status_code
```

**Result in Jaeger:**
```
Trace: abc-123-def
├─ api-gateway: POST /orders [245ms]
   └─ api-gateway: HTTP POST [200ms]
```

#### Manual Span Creation

For custom operations, create spans manually:

```python
@app.route('/orders', methods=['POST'])
def create_order():
    # Automatic span for the route
    
    with tracer.start_as_current_span("validate_order_data") as span:
        # Add custom attributes
        span.set_attribute("order.product", data['product'])
        span.set_attribute("order.quantity", data['quantity'])
        
        # Your validation logic
        validate(data)
    
    with tracer.start_as_current_span("calculate_total") as span:
        total = calculate_total(data)
        span.set_attribute("order.total", total)
    
    # Automatic span for HTTP call
    response = requests.post('http://order-service:8002/orders', json=data)
    
    return response.json()
```

**Result in Jaeger:**
```
Trace: abc-123-def
├─ api-gateway: POST /orders [245ms]
   ├─ api-gateway: validate_order_data [20ms]
   ├─ api-gateway: calculate_total [10ms]
   └─ api-gateway: HTTP POST [200ms]
```

---

## 6. Practical Implementation Examples

### 6.1 Context Propagation (The Magic!)

**The Problem:** How does Jaeger know that a request in API Gateway and a request in Order Service belong to the same trace?

**The Answer:** Context Propagation via HTTP Headers

#### How It Works:

**Step 1: API Gateway receives request**
```python
# User makes request
curl -X POST http://localhost:8080/orders

# OpenTelemetry creates a trace
# Trace ID: abc-123-def
# Span ID: span-001
```

**Step 2: API Gateway calls Order Service**
```python
# OpenTelemetry automatically injects headers!
response = requests.post('http://order-service:8002/orders', json=data)

# Headers sent (automatically):
# traceparent: 00-abc123def-span001-01
# tracestate: ...
```

**Step 3: Order Service receives request**
```python
# OpenTelemetry automatically extracts headers!
# It sees: "Oh, this request is part of trace abc-123-def"
# It creates a child span with parent span-001

# Trace ID: abc-123-def (same!)
# Span ID: span-002 (new)
# Parent Span ID: span-001
```

**Step 4: Order Service calls User Service**
```python
# OpenTelemetry propagates context again
response = requests.get('http://user-service:8001/users/1')

# Headers sent (automatically):
# traceparent: 00-abc123def-span002-01
```

**Result:** All spans share the same Trace ID and form a tree!

### 6.2 Adding Custom Attributes

```python
with tracer.start_as_current_span("process_payment") as span:
    # Business context
    span.set_attribute("payment.amount", 99.99)
    span.set_attribute("payment.currency", "USD")
    span.set_attribute("payment.method", "credit_card")
    
    # User context
    span.set_attribute("user.id", user_id)
    span.set_attribute("user.tier", "premium")
    
    # Technical context
    span.set_attribute("payment.gateway", "stripe")
    span.set_attribute("payment.api_version", "2023-10-16")
    
    # Process payment
    result = stripe.charge(amount=99.99)
    
    # Result attributes
    span.set_attribute("payment.transaction_id", result.id)
    span.set_attribute("payment.status", result.status)
```

**In Jaeger UI, you can now:**
- Search for all payments > $50: `payment.amount > 50`
- Find all Stripe payments: `payment.gateway = "stripe"`
- Filter by user tier: `user.tier = "premium"`

### 6.3 Recording Events

Events are timestamped logs within a span:

```python
with tracer.start_as_current_span("checkout") as span:
    span.add_event("Cart validation started")
    validate_cart(cart)
    
    span.add_event("Inventory check started")
    check_inventory(cart.items)
    
    span.add_event("Payment processing started", {
        "payment.amount": cart.total,
        "payment.method": "credit_card"
    })
    process_payment(cart.total)
    
    span.add_event("Order confirmation email queued", {
        "email.recipient": user.email
    })
```

**In Jaeger UI:**
```
Span: checkout [500ms]
├─ Event: Cart validation started (0ms)
├─ Event: Inventory check started (50ms)
├─ Event: Payment processing started (100ms)
│  └─ payment.amount: 99.99
│  └─ payment.method: credit_card
└─ Event: Order confirmation email queued (450ms)
   └─ email.recipient: user@example.com
```

### 6.4 Error Handling

```python
from opentelemetry.trace import Status, StatusCode

with tracer.start_as_current_span("risky_operation") as span:
    try:
        result = call_external_api()
        span.set_status(Status(StatusCode.OK))
    except TimeoutError as e:
        # Record the exception
        span.record_exception(e)
        
        # Set span status to ERROR
        span.set_status(Status(StatusCode.ERROR, "API timeout"))
        
        # Add context
        span.set_attribute("error.type", "timeout")
        span.set_attribute("error.message", str(e))
        
        raise
    except ValueError as e:
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR, "Invalid data"))
        span.set_attribute("error.type", "validation")
        raise
```

**In Jaeger UI:**
- Span appears in red (error)
- Exception stack trace is visible
- You can filter for errors: `error=true`

---

## 7. Advanced Features

### 7.1 Semantic Conventions

OpenTelemetry defines **standard attribute names** for common scenarios.

#### HTTP Requests
```python
span.set_attribute("http.method", "POST")
span.set_attribute("http.url", "https://api.example.com/users")
span.set_attribute("http.status_code", 201)
span.set_attribute("http.request_content_length", 1024)
span.set_attribute("http.response_content_length", 512)
span.set_attribute("http.user_agent", "Mozilla/5.0...")
```

#### Database Operations
```python
span.set_attribute("db.system", "postgresql")
span.set_attribute("db.name", "orders_db")
span.set_attribute("db.statement", "SELECT * FROM orders WHERE user_id = ?")
span.set_attribute("db.operation", "SELECT")
span.set_attribute("db.user", "app_user")
```

#### RPC/gRPC Calls
```python
span.set_attribute("rpc.system", "grpc")
span.set_attribute("rpc.service", "UserService")
span.set_attribute("rpc.method", "GetUser")
span.set_attribute("rpc.grpc.status_code", 0)
```

**Why use semantic conventions?**
- **Consistency** across all services
- **Compatibility** with observability tools
- **Better queries** in Jaeger/Grafana

### 7.2 Baggage (Cross-Service Context)

**Baggage** allows you to pass custom key-value pairs across service boundaries.

```python
from opentelemetry import baggage

# In API Gateway
baggage.set_baggage("user.tier", "premium")
baggage.set_baggage("request.source", "mobile_app")

# Make request to Order Service
response = requests.post('http://order-service:8002/orders', json=data)

# In Order Service (automatically propagated!)
user_tier = baggage.get_baggage("user.tier")  # "premium"
source = baggage.get_baggage("request.source")  # "mobile_app"

# Use it for business logic
if user_tier == "premium":
    apply_discount(order)
```

**Use Cases:**
- Feature flags
- A/B testing variants
- User context (tier, region, language)
- Request metadata

### 7.3 Span Links

**Span links** connect spans that are related but not in a parent-child relationship.

```python
# Scenario: Async job processing

# When creating the job
with tracer.start_as_current_span("create_job") as create_span:
    job_id = queue.enqueue(process_order, order_id)
    
    # Store the span context
    job_metadata[job_id] = {
        "trace_id": format(create_span.get_span_context().trace_id, '032x'),
        "span_id": format(create_span.get_span_context().span_id, '016x')
    }

# Later, when processing the job
with tracer.start_as_current_span("process_job") as process_span:
    # Link back to the original request
    from opentelemetry.trace import Link, SpanContext
    
    original_context = SpanContext(
        trace_id=int(job_metadata[job_id]["trace_id"], 16),
        span_id=int(job_metadata[job_id]["span_id"], 16),
        is_remote=True
    )
    
    process_span.add_link(Link(original_context))
```

**In Jaeger:** You can navigate from the async job back to the original request!

---

## 8. Best Practices

### 8.1 Naming Spans

**❌ Bad:**
```python
with tracer.start_as_current_span("operation"):
    pass

with tracer.start_as_current_span("do_stuff"):
    pass
```

**✅ Good:**
```python
with tracer.start_as_current_span("fetch_user_from_database"):
    pass

with tracer.start_as_current_span("validate_payment_card"):
    pass
```

**Rules:**
- Use descriptive names
- Use verb + noun format
- Be specific but concise
- Use lowercase with underscores

### 8.2 Attribute Cardinality

**❌ Bad (High Cardinality):**
```python
# Don't use unique IDs as attribute values
span.set_attribute("user.id", "12345")  # Millions of unique values
span.set_attribute("request.id", "abc-123-def")  # Infinite values
span.set_attribute("timestamp", "2025-11-23T15:00:00Z")  # Infinite values
```

**✅ Good (Low Cardinality):**
```python
# Use categories, not unique values
span.set_attribute("user.tier", "premium")  # ~5 values
span.set_attribute("request.source", "mobile_app")  # ~10 values
span.set_attribute("payment.method", "credit_card")  # ~5 values
```

**Why?** High cardinality attributes can overwhelm storage and make queries slow.

### 8.3 Don't Over-Instrument

**❌ Bad:**
```python
with tracer.start_as_current_span("main_operation"):
    with tracer.start_as_current_span("step_1"):
        with tracer.start_as_current_span("sub_step_1a"):
            with tracer.start_as_current_span("sub_sub_step_1a1"):
                # Too many nested spans!
                pass
```

**✅ Good:**
```python
with tracer.start_as_current_span("main_operation"):
    with tracer.start_as_current_span("validate_input"):
        validate(data)
    
    with tracer.start_as_current_span("process_data"):
        process(data)
    
    with tracer.start_as_current_span("save_result"):
        save(result)
```

**Rule:** Create spans for meaningful operations, not every function call.

### 8.4 Sampling in Production

```python
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased, ParentBased

# Sample 10% of requests
sampler = ParentBased(root=TraceIdRatioBased(0.1))

trace.set_tracer_provider(TracerProvider(sampler=sampler))
```

**Why?** Tracing every request in production is expensive. Sample 1-10% for most cases.

### 8.5 Resource Attributes

```python
from opentelemetry.sdk.resources import Resource

resource = Resource(attributes={
    # Service identity
    "service.name": "api-gateway",
    "service.version": "1.2.3",
    "service.instance.id": "api-gateway-pod-abc123",
    
    # Deployment info
    "deployment.environment": "production",
    "deployment.region": "us-east-1",
    
    # Infrastructure
    "host.name": "ip-10-0-1-42",
    "container.name": "api-gateway-container",
    "k8s.pod.name": "api-gateway-pod-abc123",
    "k8s.namespace.name": "production"
})
```

**Benefit:** Filter traces by environment, region, or instance in Jaeger.

---

## Summary

### Why OpenTelemetry?

1. **Vendor-Neutral**: Switch backends without code changes
2. **Standardized**: Consistent data format across tools
3. **Auto-Instrumentation**: Minimal code changes needed
4. **Future-Proof**: Industry standard backed by CNCF
5. **Unified**: One API for logs, metrics, and traces

### How We Use It:

1. **Install** OpenTelemetry SDK and instrumentation libraries
2. **Configure** tracer provider with service name and exporter
3. **Auto-instrument** Flask and requests library
4. **Add custom spans** for business operations
5. **Export** to Jaeger via OTLP protocol

### Key Takeaways:

- OpenTelemetry is the **standard** for observability instrumentation
- It provides **vendor-neutral** APIs for tracing, metrics, and logs
- **Auto-instrumentation** means minimal code changes
- **Context propagation** automatically links spans across services
- Use **semantic conventions** for consistent attribute names
- **Sample** in production to reduce overhead

---

## Next Steps

1. **Explore the code**: Look at `api-gateway/app.py` to see OpenTelemetry in action
2. **Run the project**: `docker-compose up -d` and generate some traffic
3. **View traces**: Open http://localhost:16686 to see traces in Jaeger
4. **Experiment**: Add custom spans and attributes to your code
5. **Read more**: https://opentelemetry.io/docs/

**You now understand why OpenTelemetry is essential and how to use it!** 🎉
