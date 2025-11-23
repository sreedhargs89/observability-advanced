import logging
import time
import uuid
import requests
from flask import Flask, request, jsonify, g
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "service": "api-gateway", "message": "%(message)s", "extra": %(extra)s}'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

from opentelemetry.sdk.resources import Resource

# Configure OpenTelemetry tracing
resource = Resource(attributes={
    "service.name": "api-gateway"
})
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

# Configure OTLP exporter
otlp_exporter = OTLPSpanExporter(endpoint="http://jaeger:4317", insecure=True)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(otlp_exporter)
)

# Auto-instrument Flask and requests
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

# Prometheus metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

http_requests_active = Gauge(
    'http_requests_active',
    'Active HTTP requests'
)

# Service URLs
USER_SERVICE_URL = "http://user-service:8001"
ORDER_SERVICE_URL = "http://order-service:8002"


def get_correlation_id():
    """Get or generate correlation ID for request tracking"""
    return request.headers.get('X-Correlation-ID', str(uuid.uuid4()))


def log_with_context(level, message, **kwargs):
    """Log with correlation ID and trace context"""
    from flask import has_request_context
    
    span = trace.get_current_span()
    trace_id = format(span.get_span_context().trace_id, '032x') if span else 'no-trace'
    
    extra_data = {
        'correlation_id': g.get('correlation_id', 'unknown') if has_request_context() else 'startup',
        'trace_id': trace_id,
        **kwargs
    }
    
    logger.log(level, message, extra={'extra': str(extra_data).replace("'", '"')})


@app.before_request
def before_request():
    """Set up request context"""
    g.correlation_id = get_correlation_id()
    g.start_time = time.time()
    http_requests_active.inc()
    
    log_with_context(
        logging.INFO,
        "Incoming request",
        method=request.method,
        path=request.path,
        remote_addr=request.remote_addr
    )


@app.after_request
def after_request(response):
    """Log response and record metrics"""
    duration = time.time() - g.start_time
    
    # Record metrics
    http_requests_total.labels(
        method=request.method,
        endpoint=request.endpoint or 'unknown',
        status=response.status_code
    ).inc()
    
    http_request_duration_seconds.labels(
        method=request.method,
        endpoint=request.endpoint or 'unknown'
    ).observe(duration)
    
    http_requests_active.dec()
    
    # Log response
    log_with_context(
        logging.INFO,
        "Outgoing response",
        method=request.method,
        path=request.path,
        status_code=response.status_code,
        duration_ms=round(duration * 1000, 2)
    )
    
    # Add correlation ID to response headers
    response.headers['X-Correlation-ID'] = g.correlation_id
    
    return response


def proxy_request(service_url, path, method='GET', data=None):
    """Proxy request to backend service with trace context"""
    with tracer.start_as_current_span(f"proxy_to_{service_url.split('//')[1].split(':')[0]}") as span:
        url = f"{service_url}{path}"
        headers = {'X-Correlation-ID': g.correlation_id}
        
        span.set_attribute("http.url", url)
        span.set_attribute("http.method", method)
        
        log_with_context(
            logging.DEBUG,
            "Proxying request to backend",
            url=url,
            method=method
        )
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                return jsonify({"error": "Method not supported"}), 405
            
            span.set_attribute("http.status_code", response.status_code)
            
            log_with_context(
                logging.DEBUG,
                "Received response from backend",
                url=url,
                status_code=response.status_code
            )
            
            return response.json(), response.status_code
            
        except requests.exceptions.Timeout:
            log_with_context(
                logging.ERROR,
                "Backend service timeout",
                url=url
            )
            span.set_attribute("error", True)
            return jsonify({"error": "Service timeout"}), 504
            
        except requests.exceptions.ConnectionError:
            log_with_context(
                logging.ERROR,
                "Cannot connect to backend service",
                url=url
            )
            span.set_attribute("error", True)
            return jsonify({"error": "Service unavailable"}), 503
            
        except Exception as e:
            log_with_context(
                logging.ERROR,
                "Error proxying request",
                url=url,
                error=str(e)
            )
            span.record_exception(e)
            span.set_attribute("error", True)
            return jsonify({"error": "Internal server error"}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "api-gateway"}), 200


@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


@app.route('/', methods=['GET'])
def index():
    """API documentation"""
    return jsonify({
        "service": "API Gateway",
        "version": "1.0.0",
        "endpoints": {
            "users": {
                "GET /users": "List all users",
                "GET /users/<id>": "Get user by ID",
                "POST /users": "Create user",
                "DELETE /users/<id>": "Delete user"
            },
            "orders": {
                "GET /orders": "List all orders",
                "GET /orders/<id>": "Get order by ID",
                "POST /orders": "Create order",
                "DELETE /orders/<id>": "Delete order"
            }
        },
        "observability": {
            "prometheus": "http://localhost:9090",
            "jaeger": "http://localhost:16686",
            "grafana": "http://localhost:3000"
        }
    }), 200


# User service routes
@app.route('/users', methods=['GET'])
def get_users():
    """Get all users"""
    return proxy_request(USER_SERVICE_URL, '/users')


@app.route('/users/<user_id>', methods=['GET'])
def get_user(user_id):
    """Get user by ID"""
    return proxy_request(USER_SERVICE_URL, f'/users/{user_id}')


@app.route('/users', methods=['POST'])
def create_user():
    """Create a new user"""
    return proxy_request(USER_SERVICE_URL, '/users', method='POST', data=request.get_json())


@app.route('/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete a user"""
    return proxy_request(USER_SERVICE_URL, f'/users/{user_id}', method='DELETE')


# Order service routes
@app.route('/orders', methods=['GET'])
def get_orders():
    """Get all orders"""
    return proxy_request(ORDER_SERVICE_URL, '/orders')


@app.route('/orders/<order_id>', methods=['GET'])
def get_order(order_id):
    """Get order by ID"""
    return proxy_request(ORDER_SERVICE_URL, f'/orders/{order_id}')


@app.route('/orders', methods=['POST'])
def create_order():
    """Create a new order"""
    return proxy_request(ORDER_SERVICE_URL, '/orders', method='POST', data=request.get_json())


@app.route('/orders/<order_id>', methods=['DELETE'])
def delete_order(order_id):
    """Delete an order"""
    return proxy_request(ORDER_SERVICE_URL, f'/orders/{order_id}', method='DELETE')


@app.errorhandler(Exception)
def handle_error(error):
    """Global error handler"""
    span = trace.get_current_span()
    if span:
        span.record_exception(error)
        span.set_attribute("error", True)
    
    log_with_context(
        logging.ERROR,
        "Unhandled exception",
        error=str(error),
        error_type=type(error).__name__
    )
    
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    log_with_context(
        logging.INFO,
        "Starting API gateway",
        port=8080
    )
    app.run(host='0.0.0.0', port=8080, debug=False)
