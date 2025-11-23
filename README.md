## 📚 What You'll Learn

- **What is Observability?** Understanding the difference between monitoring and observability
- **The Three Pillars:**
  - 📝 **Logs** - Structured logging for debugging
  - 📊 **Metrics** - Quantitative data about your system
  - 🔍 **Traces** - Request flows across distributed services
- **Practical Tools:**
  - Prometheus for metrics collection
  - Jaeger for distributed tracing
  - Grafana for visualization
  - OpenTelemetry for instrumentation

## 🏗️ Project Overview

We'll build a simple e-commerce microservices application:

```
┌─────────────┐
│ API Gateway │ (Port 8080)
└──────┬──────┘
       │
       ├─────────────┐
       │             │
┌──────▼──────┐ ┌───▼────────┐
│User Service │ │Order Service│
│ (Port 8001) │ │ (Port 8002)│
└─────────────┘ └─────────────┘
```

**Observability Stack:**
- **Prometheus** (Port 9090) - Metrics storage and querying
- **Jaeger** (Port 16686) - Distributed tracing UI
- **Grafana** (Port 3000) - Dashboards and visualization

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Basic understanding of REST APIs
- Curiosity about observability!

### Start the Stack

```bash
cd observability-tutorial
docker-compose up -d
```

### Access the Services

- **API Gateway**: http://localhost:8080
- **Prometheus**: http://localhost:9090
- **Jaeger UI**: http://localhost:16686
- **Grafana**: http://localhost:3000 (admin/admin)

### Generate Some Traffic

```bash
# Create a user
curl -X POST http://localhost:8080/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "email": "alice@example.com"}'

# Create an order
curl -X POST http://localhost:8080/orders \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1", "product": "Laptop", "quantity": 1}'

# Get user details
curl http://localhost:8080/users/1

# Get order details
curl http://localhost:8080/orders/1
```

## 📖 Tutorial Path

Follow these guides in order:

1. **[Introduction to Observability](docs/01-introduction.md)**
   - What is observability and why it matters
   - The three pillars explained
   - Observability vs Monitoring

2. **[Logging Deep Dive](docs/02-logging.md)**
   - Structured logging best practices
   - Log levels and when to use them
   - Viewing logs in our services

3. **[Metrics Explained](docs/03-metrics.md)**
   - Types of metrics (counters, gauges, histograms)
   - The RED method (Rate, Errors, Duration)
   - Using Prometheus and Grafana

4. **[Distributed Tracing](docs/04-tracing.md)**
   - Understanding spans and traces
   - Context propagation across services
   - Debugging with Jaeger

5. **[Putting It All Together](docs/05-putting-it-together.md)**
   - Practical debugging scenarios
   - Setting up alerts
   - Production best practices

## 🎯 Learning Exercises

Each tutorial section includes hands-on exercises:

- **Exercise 1**: Find slow requests using traces
- **Exercise 2**: Create a custom metric
- **Exercise 3**: Debug a failing service with logs
- **Exercise 4**: Build a Grafana dashboard
- **Exercise 5**: Simulate and detect an outage

## 🛠️ Project Structure

```
observability-tutorial/
├── api-gateway/          # API Gateway service
├── user-service/         # User management service
├── order-service/        # Order processing service
├── prometheus/           # Prometheus configuration
├── grafana/             # Grafana dashboards and config
├── docs/                # Tutorial documentation
├── docker-compose.yml   # Complete stack definition
└── README.md           # This file
```

## 🔍 Key Concepts

### Observability vs Monitoring

**Monitoring** tells you *when* something is wrong.  
**Observability** helps you understand *why* it's wrong.

### The Three Pillars

| Pillar | Purpose | Example |
|--------|---------|---------|
| **Logs** | Discrete events | "User 123 logged in at 10:30 AM" |
| **Metrics** | Aggregated measurements | "Average response time: 250ms" |
| **Traces** | Request journey | "Request took 500ms across 3 services" |

### Why All Three?

- **Logs** provide detailed context for specific events
- **Metrics** show trends and patterns over time
- **Traces** reveal relationships between distributed components

Together, they give you complete visibility into your system's behavior.

## 🎓 Best Practices You'll Learn

- ✅ Structured logging with correlation IDs
- ✅ Meaningful metric names and labels
- ✅ Proper trace context propagation
- ✅ Setting up useful dashboards
- ✅ Alerting on SLOs (Service Level Objectives)
- ✅ Debugging production issues efficiently

## 🧹 Cleanup

```bash
# Stop all services
docker-compose down

# Remove volumes (optional)
docker-compose down -v
```

## 📚 Additional Resources

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [Grafana Tutorials](https://grafana.com/tutorials/)

## 🤝 Next Steps

1. Start with [Introduction to Observability](docs/01-introduction.md)
2. Run the services and explore the UIs
3. Complete the exercises in each section
4. Experiment with your own modifications!

---

**Ready to begin?** Head to [docs/01-introduction.md](docs/01-introduction.md) to start your observability journey! 🚀
