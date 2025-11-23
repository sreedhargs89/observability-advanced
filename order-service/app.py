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
from opentelemetry.trace import Status, StatusCode

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "service": "order-service", "message": "%(message)s", "extra": %(extra)s}'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

from opentelemetry.sdk.resources import Resource

# Configure OpenTelemetry tracing
resource = Resource(attributes={
    "service.name": "order-service"
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

orders_created_total = Counter(
    'orders_created_total',
    'Total orders created',
    ['product']
)

order_value_total = Counter(
    'order_value_total',
    'Total order value in dollars'
)

# In-memory order storage (for demo purposes)
orders_db = {}
order_id_counter = 1

# User service URL
USER_SERVICE_URL = "http://user-service:8001"


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
    return jsonify({"status": "healthy", "service": "order-service"}), 200


@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


@app.route('/orders', methods=['GET'])
def get_orders():
    """Get all orders"""
    with tracer.start_as_current_span("get_orders") as span:
        span.set_attribute("order.count", len(orders_db))
        
        log_with_context(
            logging.INFO,
            "Fetching all orders",
            order_count=len(orders_db)
        )
        
        return jsonify(list(orders_db.values())), 200


@app.route('/orders/<order_id>', methods=['GET'])
def get_order(order_id):
    """Get order by ID"""
    with tracer.start_as_current_span("get_order") as span:
        span.set_attribute("order.id", order_id)
        
        log_with_context(
            logging.INFO,
            "Fetching order",
            order_id=order_id
        )
        
        if order_id not in orders_db:
            log_with_context(
                logging.WARNING,
                "Order not found",
                order_id=order_id
            )
            span.set_attribute("error", True)
            return jsonify({"error": "Order not found"}), 404
        
        order = orders_db[order_id]
        
        log_with_context(
            logging.INFO,
            "Order found",
            order_id=order_id,
            product=order['product']
        )
        
        return jsonify(order), 200


@app.route('/orders', methods=['POST'])
def create_order():
    """Create a new order"""
    global order_id_counter
    
    with tracer.start_as_current_span("create_order") as span:
        data = request.get_json()
        
        # Validate input
        if not data or 'user_id' not in data or 'product' not in data or 'quantity' not in data:
            log_with_context(
                logging.ERROR,
                "Invalid order data",
                data=data
            )
            span.set_attribute("error", True)
            return jsonify({"error": "Missing required fields: user_id, product, quantity"}), 400
        
        user_id = data['user_id']
        product = data['product']
        quantity = int(data['quantity'])
        
        # Add span attributes
        span.set_attribute("order.user_id", user_id)
        span.set_attribute("order.product", product)
        span.set_attribute("order.quantity", quantity)
        
        # Validate user exists (call user service)
        with tracer.start_as_current_span("validate_user") as user_span:
            user_span.set_attribute("user.id", user_id)
            
            log_with_context(
                logging.INFO,
                "Validating user",
                user_id=user_id
            )
            
            try:
                # Pass correlation ID to downstream service
                headers = {'X-Correlation-ID': g.correlation_id}
                user_response = requests.get(
                    f"{USER_SERVICE_URL}/users/{user_id}",
                    headers=headers,
                    timeout=5
                )
                
                if user_response.status_code == 404:
                    log_with_context(
                        logging.WARNING,
                        "User not found",
                        user_id=user_id
                    )
                    user_span.set_attribute("error", True)
                    span.set_attribute("error", True)
                    return jsonify({"error": "User not found"}), 404
                
                if user_response.status_code != 200:
                    log_with_context(
                        logging.ERROR,
                        "User service error",
                        user_id=user_id,
                        status_code=user_response.status_code
                    )
                    user_span.set_attribute("error", True)
                    span.set_attribute("error", True)
                    return jsonify({"error": "Failed to validate user"}), 500
                
                user_data = user_response.json()
                log_with_context(
                    logging.INFO,
                    "User validated successfully",
                    user_id=user_id,
                    user_email=user_data.get('email')
                )
                
            except requests.exceptions.RequestException as e:
                log_with_context(
                    logging.ERROR,
                    "Failed to connect to user service",
                    user_id=user_id,
                    error=str(e)
                )
                user_span.record_exception(e)
                user_span.set_status(Status(StatusCode.ERROR, str(e)))
                span.set_attribute("error", True)
                return jsonify({"error": "Service unavailable"}), 503
        
        # Calculate order total (simple pricing)
        with tracer.start_as_current_span("calculate_total") as calc_span:
            # SIMULATE FAILURE: If product is 'fail_product', crash!
            if product == "fail_product":
                error_msg = "Payment gateway timeout: Unable to reach provider"
                log_with_context(
                    logging.ERROR,
                    "Payment processing failed",
                    reason=error_msg,
                    product=product
                )
                raise ValueError(error_msg)

            price_per_item = 99.99  # Demo price
            total = price_per_item * quantity
            calc_span.set_attribute("order.total", total)
            
            log_with_context(
                logging.DEBUG,
                "Calculated order total",
                quantity=quantity,
                price_per_item=price_per_item,
                total=total
            )
        
        # Create order
        with tracer.start_as_current_span("save_order") as save_span:
            order_id = str(order_id_counter)
            order_id_counter += 1
            
            order = {
                "id": order_id,
                "user_id": user_id,
                "product": product,
                "quantity": quantity,
                "total": total,
                "status": "pending",
                "created_at": time.time()
            }
            
            orders_db[order_id] = order
            save_span.set_attribute("order.id", order_id)
            
            log_with_context(
                logging.INFO,
                "Order saved to database",
                order_id=order_id
            )
        
        # Record business metrics
        orders_created_total.labels(product=product).inc()
        order_value_total.inc(total)
        
        # Add final span attributes
        span.set_attribute("order.id", order_id)
        span.set_attribute("order.total", total)
        
        # Log order creation
        log_with_context(
            logging.INFO,
            "Order created successfully",
            order_id=order_id,
            user_id=user_id,
            product=product,
            quantity=quantity,
            total=total
        )
        
        return jsonify(order), 201


@app.route('/orders/<order_id>', methods=['DELETE'])
def delete_order(order_id):
    """Delete an order"""
    with tracer.start_as_current_span("delete_order") as span:
        span.set_attribute("order.id", order_id)
        
        if order_id not in orders_db:
            log_with_context(
                logging.WARNING,
                "Cannot delete: Order not found",
                order_id=order_id
            )
            span.set_attribute("error", True)
            return jsonify({"error": "Order not found"}), 404
        
        order = orders_db.pop(order_id)
        
        log_with_context(
            logging.INFO,
            "Order deleted",
            order_id=order_id,
            product=order['product']
        )
        
        return jsonify({"message": "Order deleted"}), 200


@app.errorhandler(Exception)
def handle_error(error):
    """Global error handler"""
    import traceback
    
    span = trace.get_current_span()
    if span:
        span.record_exception(error)
        span.set_attribute("error", True)
    
    # Get stack trace information
    tb = traceback.extract_tb(error.__traceback__)
    if tb:
        # Get the last frame (where the error actually occurred)
        last_frame = tb[-1]
        file_name = last_frame.filename.split('/')[-1]  # Just the filename
        line_number = last_frame.lineno
        function_name = last_frame.name
    else:
        file_name = "unknown"
        line_number = 0
        function_name = "unknown"
    
    log_with_context(
        logging.ERROR,
        "Unhandled exception",
        error=str(error),
        error_type=type(error).__name__,
        file=file_name,
        line=line_number,
        function=function_name,
        stack_trace=traceback.format_exc()
    )
    
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    log_with_context(
        logging.INFO,
        "Starting order service",
        port=8002
    )
    app.run(host='0.0.0.0', port=8002, debug=False)
