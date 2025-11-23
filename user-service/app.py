import logging
import time
import uuid
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
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "service": "user-service", "message": "%(message)s", "extra": %(extra)s}'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

from opentelemetry.sdk.resources import Resource

# Configure OpenTelemetry tracing
resource = Resource(attributes={
    "service.name": "user-service"
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

users_created_total = Counter(
    'users_created_total',
    'Total users created'
)

# In-memory user storage (for demo purposes)
users_db = {}
user_id_counter = 1


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


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "user-service"}), 200


@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


@app.route('/users', methods=['GET'])
def get_users():
    """Get all users"""
    with tracer.start_as_current_span("get_users") as span:
        span.set_attribute("user.count", len(users_db))
        
        log_with_context(
            logging.INFO,
            "Fetching all users",
            user_count=len(users_db)
        )
        
        return jsonify(list(users_db.values())), 200


@app.route('/users/<user_id>', methods=['GET'])
def get_user(user_id):
    """Get user by ID"""
    with tracer.start_as_current_span("get_user") as span:
        span.set_attribute("user.id", user_id)
        
        log_with_context(
            logging.INFO,
            "Fetching user",
            user_id=user_id
        )
        
        if user_id not in users_db:
            log_with_context(
                logging.WARNING,
                "User not found",
                user_id=user_id
            )
            span.set_attribute("error", True)
            return jsonify({"error": "User not found"}), 404
        
        user = users_db[user_id]
        
        log_with_context(
            logging.INFO,
            "User found",
            user_id=user_id,
            user_email=user['email']
        )
        
        return jsonify(user), 200


@app.route('/users', methods=['POST'])
def create_user():
    """Create a new user"""
    global user_id_counter
    
    with tracer.start_as_current_span("create_user") as span:
        data = request.get_json()
        
        # Validate input
        if not data or 'name' not in data or 'email' not in data:
            log_with_context(
                logging.ERROR,
                "Invalid user data",
                data=data
            )
            span.set_attribute("error", True)
            return jsonify({"error": "Missing required fields: name, email"}), 400
        
        # Create user
        user_id = str(user_id_counter)
        user_id_counter += 1
        
        user = {
            "id": user_id,
            "name": data['name'],
            "email": data['email'],
            "created_at": time.time()
        }
        
        users_db[user_id] = user
        
        # Record metrics
        users_created_total.inc()
        
        # Add span attributes
        span.set_attribute("user.id", user_id)
        span.set_attribute("user.email", user['email'])
        
        # Log user creation
        log_with_context(
            logging.INFO,
            "User created successfully",
            user_id=user_id,
            user_email=user['email'],
            user_name=user['name']
        )
        
        return jsonify(user), 201


@app.route('/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete a user"""
    with tracer.start_as_current_span("delete_user") as span:
        span.set_attribute("user.id", user_id)
        
        if user_id not in users_db:
            log_with_context(
                logging.WARNING,
                "Cannot delete: User not found",
                user_id=user_id
            )
            span.set_attribute("error", True)
            return jsonify({"error": "User not found"}), 404
        
        user = users_db.pop(user_id)
        
        log_with_context(
            logging.INFO,
            "User deleted",
            user_id=user_id,
            user_email=user['email']
        )
        
        return jsonify({"message": "User deleted"}), 200


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
        "Starting user service",
        port=8001
    )
    app.run(host='0.0.0.0', port=8001, debug=False)
