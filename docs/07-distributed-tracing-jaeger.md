# Distributed Tracing with Jaeger

## 1. What is Distributed Tracing?

In a microservices architecture, a single user request can trigger a cascade of calls across multiple services. For example, when a user places an order:
1. **API Gateway** receives the request
2. **API Gateway** calls **User Service** to validate the user
3. **API Gateway** calls **Order Service** to create the order
4. **Order Service** calls **User Service** again to fetch user details

If this request takes 5 seconds, which service is the bottleneck? **Distributed Tracing** answers this question by tracking the request's journey across all services.

---

## 2. What is Jaeger?

**Jaeger** is an open-source, end-to-end distributed tracing system originally developed by Uber. It helps you:
*   **Visualize** the flow of requests through your microservices
*   **Identify** performance bottlenecks
*   **Debug** complex distributed systems
*   **Monitor** service dependencies

### Why Jaeger is Needed

| Problem | Without Tracing | With Jaeger |
|---------|----------------|-------------|
| **Slow Request** | "The API is slow" (no idea which service) | "Order Service took 4.8s out of 5s total" |
| **Error Debugging** | Check logs in 10 different services | See the exact span where the error occurred |
| **Service Dependencies** | Manually document or guess | Auto-generated dependency graph |
| **Performance Regression** | "It was faster last week" | Compare trace durations over time |

---

## 3. Key Concepts

### Trace
A **trace** represents the entire journey of a single request through your system. It has a unique **Trace ID** that is propagated across all services.

**Example from our setup:**
![Jaeger Trace Waterfall](images/jaeger_trace_waterfall.png)

In the screenshot above, you can see a complete trace showing how a single POST request to create an order flows through:
1. **api-gateway** (top span) - Entry point
2. **proxy_to_order-service** - API Gateway forwarding to Order Service
3. **order-service** - Processing the order
4. **validate_user** - Order Service calling User Service to verify the user exists

All these operations share the same Trace ID, allowing Jaeger to group them together.

### Span
A **span** represents a single operation within a trace. Each span has:
*   **Operation Name**: e.g., "GET /users", "validate_user", "database_query"
*   **Start Time** and **Duration**
*   **Tags**: Key-value metadata (e.g., `http.status_code=200`, `user.id=123`)
*   **Logs**: Timestamped events within the span
*   **Parent Span ID**: Links it to the calling operation

**Example from our setup:**
![Jaeger Span Details](images/jaeger_span_details.png)

In this screenshot, you can see the details of the `proxy_to_order-service` span, including:
- **Duration**: How long this operation took
- **Tags**: Metadata like `http.method=POST`, `http.status_code=201`, `http.url=http://order-service:8002/orders`
- **Process**: Which service created this span (api-gateway)
- **References**: The parent span that called this operation

### Context Propagation
When Service A calls Service B, it passes the **Trace ID** and **Span ID** in HTTP headers. This is how Jaeger knows that both operations belong to the same request.

In our implementation, we use **OpenTelemetry** to automatically inject these headers:
```
X-B3-TraceId: 80f198ee56343ba864fe8b2a57d3eff7
X-B3-SpanId: e457b5a2e4d86bd1
X-B3-ParentSpanId: 05e3ac9a4f6e3b90
```

**Visualizing Service Communication:**
![Jaeger Dependencies](images/jaeger_dependencies.png)

This dependency graph shows how our services communicate:
- **api-gateway** → **order-service**: API Gateway forwards order creation requests
- **api-gateway** → **user-service**: API Gateway forwards user-related requests
- **order-service** → **user-service**: Order Service validates users before creating orders

The arrows show the direction of calls, and this graph is automatically generated from the trace data!

---

## 4. Implementation in Our Project

### Architecture
We configured all three services (API Gateway, User Service, Order Service) to send traces to Jaeger using the **OTLP (OpenTelemetry Protocol)** exporter.

```python
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

# Define service name
resource = Resource(attributes={
    "service.name": "api-gateway"
})

# Configure tracer
trace.set_tracer_provider(TracerProvider(resource=resource))
otlp_exporter = OTLPSpanExporter(endpoint="http://jaeger:4317", insecure=True)
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))
```

### Auto-Instrumentation
We use **FlaskInstrumentor** and **RequestsInstrumentor** to automatically create spans for:
*   Incoming HTTP requests (Flask routes)
*   Outgoing HTTP requests (calls to other services)

```python
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()
```

This means we don't have to manually create spans for every HTTP call—OpenTelemetry does it for us!

---

## 5. Reading Traces in Jaeger UI

Now that you understand the concepts, let's see how to use the Jaeger UI to debug issues.

### Finding Traces
1. Open Jaeger UI at `http://localhost:16686`
2. Select a service from the dropdown (e.g., `api-gateway`)
3. Click "Find Traces"
4. You'll see a list of recent traces with their duration and span count

### Analyzing the Waterfall
As shown in the trace waterfall screenshot earlier:
*   **Horizontal bars**: Each bar represents a span (an operation)
*   **Length of bar**: The duration of that operation
*   **Nesting**: Child spans are indented under their parent
*   **Colors**: Different services have different colors

**How to identify bottlenecks:**
- Look for the longest bars—these are your slow operations
- Check if spans are sequential (one after another) or parallel
- Compare similar traces to see if one is abnormally slow

### Understanding Span Details
Click any span to see its details (as shown in the span details screenshot):
*   **Tags**: Searchable metadata about the operation
*   **Process**: Which service and instance executed this span
*   **Logs**: Events that occurred during the span execution
*   **Duration**: Exact timing information

### Using the Dependencies Graph
The dependencies view (shown earlier) helps you:
*   Understand your system architecture at a glance
*   Identify which services talk to each other
*   Spot unexpected dependencies or circular calls
*   Plan for service decomposition or consolidation

---

## 6. How Context Propagation Works

Let's trace a single request step-by-step:

### Step 1: User sends request
```bash
curl -X POST http://localhost:8080/orders \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1", "product": "laptop", "quantity": 1}'
```

### Step 2: API Gateway creates root span
```python
# OpenTelemetry automatically creates a span for the incoming request
# Trace ID: abc123 (generated)
# Span ID: span-001
# Operation: POST /orders
```

### Step 3: API Gateway calls Order Service
```python
# When making the HTTP request, OpenTelemetry injects headers:
headers = {
    'X-B3-TraceId': 'abc123',        # Same trace!
    'X-B3-ParentSpanId': 'span-001'  # Parent is API Gateway
}
requests.post('http://order-service:8002/orders', headers=headers, json=data)
```

### Step 4: Order Service creates child span
```python
# Order Service extracts the Trace ID from headers
# Trace ID: abc123 (inherited)
# Span ID: span-002 (new)
# Parent Span ID: span-001
# Operation: POST /orders (in Order Service)
```

### Step 5: Order Service calls User Service
```python
# Order Service propagates the context again:
headers = {
    'X-B3-TraceId': 'abc123',        # Still the same trace!
    'X-B3-ParentSpanId': 'span-002'  # Parent is now Order Service
}
requests.get('http://user-service:8001/users/1', headers=headers)
```

### Step 6: User Service creates grandchild span
```python
# User Service extracts the Trace ID
# Trace ID: abc123 (inherited)
# Span ID: span-003 (new)
# Parent Span ID: span-002
# Operation: GET /users/1
```

### Result
All three spans (`span-001`, `span-002`, `span-003`) share the same **Trace ID** (`abc123`). Jaeger groups them together and displays them as a single trace with a waterfall view.

---

## 10. Advantages of Jaeger

1.  **Performance Analysis**: Instantly see which service is slow
2.  **Error Tracking**: See the exact span where an exception occurred
3.  **Dependency Mapping**: Auto-generate service architecture diagrams
4.  **Root Cause Analysis**: Drill down from a high-level metric spike to the specific slow database query
5.  **Sampling**: In production, you can sample (e.g., trace 1% of requests) to reduce overhead

---

## 8. Complete Workflow: From Jaeger to Loki

Let's walk through a real debugging scenario using our observability stack.

### Scenario: Payment Gateway Timeout

We've simulated a failure where ordering a product called `fail_product` causes a "Payment gateway timeout" error. Here's how we debug it:

### Step 1: Detect the Error in Jaeger

First, we search for traces in the `order-service`:

![Jaeger Failed Trace](images/jaeger_failed_trace.png)

**What we see:**
- The trace shows an error (indicated by the red error icon)
- The `calculate_total` span is where the failure occurred
- The error happened in the Order Service, not in the API Gateway or User Service
- Total duration shows the request failed quickly (not a timeout, but an immediate error)

### Step 2: Identify the Trace ID

At the top of the trace details, we can see the **Trace ID**:

![Jaeger Trace ID](images/jaeger_trace_id.png)

This Trace ID is crucial—it's the link between Jaeger (tracing) and Loki (logs). Every log entry from this request will have this same Trace ID embedded in it.

### Step 3: Search for Logs in Loki

Now we navigate to Grafana Explore and query Loki for logs related to this error:

**Query:** `{service="order-service"} |= "Payment gateway timeout"`

![Loki Error Logs](images/loki_error_logs_from_trace.png)

**What we see:**
- Multiple log entries matching our error message
- Each log line shows the timestamp, service name, and a preview of the error
- We can see these errors occurred recently (matching our test)

### Step 4: Examine the Log Details

Expanding one of the log entries shows the complete context:

![Loki Log Details with Trace](images/loki_log_details_with_trace.png)

**Critical information revealed:**
- **Error Message**: "Payment processing failed"
- **Reason**: "Payment gateway timeout: Unable to reach provider"
- **Product**: "fail_product" (the trigger)
- **Trace ID**: Links back to the Jaeger trace we just viewed
- **Correlation ID**: Allows tracking this request across all logs

### Step 5: Root Cause Analysis

By combining Jaeger and Loki, we now have the complete picture:

| Tool | What it told us |
|------|----------------|
| **Jaeger** | The error occurred in the `calculate_total` span of the Order Service |
| **Loki** | The specific error is "Payment gateway timeout: Unable to reach provider" for product "fail_product" |
| **Conclusion** | The Order Service is trying to contact a payment gateway that is unreachable when processing this specific product |

### The Power of Trace ID Correlation

Notice how the **Trace ID** appears in both:
1. **Jaeger**: At the top of the trace view
2. **Loki**: Inside the log message's `trace_id` field

This correlation is automatic because our code logs the trace ID:
```python
span = trace.get_current_span()
trace_id = format(span.get_span_context().trace_id, '032x')
log_with_context(logging.ERROR, "Payment processing failed", trace_id=trace_id, ...)
```

This means you can:
- Start in Jaeger → Copy Trace ID → Search in Loki
- Start in Loki → Copy Trace ID → Search in Jaeger
- Or use Grafana's built-in trace-to-logs linking (in production setups)

---

## 9. Integration with Metrics and Logs

Jaeger works best when combined with Prometheus and Loki:

| Tool | Question | Example |
|------|----------|---------|
| **Prometheus** | "Is there a problem?" | Error rate spiked to 10% |
| **Jaeger** | "Where is the problem?" | Order Service → Payment API call is timing out |
| **Loki** | "Why is it happening?" | Logs show "Connection refused to payment-gateway.external.com" |

**Workflow:**
1.  Prometheus alerts you: "Order Service error rate > 5%"
2.  You open Jaeger and filter for failed traces
3.  You see the Payment API span is red (error)
4.  You click the span and see the error message
5.  You copy the **Trace ID** and search for it in Loki
6.  Loki shows the full stack trace and error context

This is the power of **unified observability**!
