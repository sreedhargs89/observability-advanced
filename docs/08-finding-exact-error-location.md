# Finding the Exact File and Line Number from Logs

## The Question

When you see an error log like this in Loki:
```json
{
  "error": "Payment gateway timeout: Unable to reach provider",
  "error_type": "ValueError",
  "service": "order-service"
}
```

**How do you know which file and which line of code caused it?**

---

## The Answer: Enhanced Error Logging

We've enhanced our error handler to automatically capture and log:
- **File name** - Which Python file the error occurred in
- **Line number** - The exact line that raised the exception
- **Function name** - Which function was executing
- **Stack trace** - The complete call stack showing how we got there

### The Code Enhancement

In `order-service/app.py`, we modified the global error handler:

```python
@app.errorhandler(Exception)
def handle_error(error):
    """Global error handler"""
    import traceback
    
    # Record exception in trace
    span = trace.get_current_span()
    if span:
        span.record_exception(error)
        span.set_attribute("error", True)
    
    # Extract file location from stack trace
    tb = traceback.extract_tb(error.__traceback__)
    if tb:
        last_frame = tb[-1]  # Where the error actually occurred
        file_name = last_frame.filename.split('/')[-1]
        line_number = last_frame.lineno
        function_name = last_frame.name
    else:
        file_name = "unknown"
        line_number = 0
        function_name = "unknown"
    
    # Log with complete context
    log_with_context(
        logging.ERROR,
        "Unhandled exception",
        error=str(error),
        error_type=type(error).__name__,
        file=file_name,           # NEW: File name
        line=line_number,          # NEW: Line number
        function=function_name,    # NEW: Function name
        stack_trace=traceback.format_exc()  # NEW: Full stack trace
    )
    
    return jsonify({"error": "Internal server error"}), 500
```

---

## Viewing the Enhanced Logs in Loki

When you expand a log entry in Loki, you now see:

![Loki Detailed Error Info](images/loki_detailed_error_info.png)

### What the Screenshot Shows:

1. **file: "app.py"** - The error occurred in the `app.py` file
2. **line: 311** - Specifically at line 311
3. **function: "create_order"** - Inside the `create_order` function
4. **stack_trace** - The complete call stack:
   ```
   File "/app/app.py", line 311, in create_order
       raise ValueError(error_msg)
   ValueError: Payment gateway timeout: Unable to reach provider
   ```

### How to Use This Information:

1. **Open the file**: `order-service/app.py`
2. **Go to line 311**: This is where `raise ValueError(error_msg)` is called
3. **Understand the context**: The `create_order` function is processing an order
4. **Fix the issue**: You now know exactly where to look!

---

## The Complete Debugging Flow

### Step 1: See the error in Prometheus/Grafana
"Order Service error rate is high"

### Step 2: Find the trace in Jaeger
"The error is in the `calculate_total` span"

### Step 3: Search Loki for the error message
Query: `{service="order-service"} |= "Payment gateway timeout"`

### Step 4: Expand the log to see file details
- **File**: `app.py`
- **Line**: `311`
- **Function**: `create_order`
- **Stack Trace**: Full Python traceback

### Step 5: Open your code editor
```bash
code order-service/app.py:311
```

You're now looking at the exact line that caused the error!

---

## Why This Matters

Without this enhancement, you would have to:
1. Guess which file based on the service name
2. Search the entire codebase for the error message
3. Add print statements and redeploy
4. Hope you find it

**With this enhancement:**
- You know the exact file in **1 second**
- You know the exact line in **1 second**
- You can fix it **immediately**

This is the difference between **hours of debugging** and **minutes of debugging**.

---

## Best Practices

### 1. Always Log Stack Traces for Errors
```python
import traceback
log.error("Error occurred", stack_trace=traceback.format_exc())
```

### 2. Include Context in Logs
```python
log.error(
    "Payment failed",
    user_id=user_id,
    product=product,
    amount=amount,
    file=__file__,
    line=sys._getframe().f_lineno
)
```

### 3. Use Structured Logging
JSON format makes it easy to search and filter:
```json
{
  "level": "ERROR",
  "message": "Payment failed",
  "user_id": "123",
  "file": "app.py",
  "line": 311
}
```

### 4. Correlate with Trace IDs
Always include the trace ID so you can jump between Jaeger and Loki:
```python
trace_id = format(span.get_span_context().trace_id, '032x')
log.error("Error", trace_id=trace_id, ...)
```

---

## Summary

| Before Enhancement | After Enhancement |
|-------------------|-------------------|
| "Error in order-service" | "Error in `app.py` line 311" |
| Search entire codebase | Open file directly |
| Guess and check | Know immediately |
| Hours to debug | Minutes to debug |

The key is **capturing the stack trace** and **extracting the file location** automatically in your error handler!
