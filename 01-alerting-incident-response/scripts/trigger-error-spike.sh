#!/bin/bash

# Script to trigger a high error rate for testing alerts
# This simulates a production incident

echo "🔥 Triggering error spike in order-service..."
echo "This will cause the HighErrorRate alert to fire in ~5 minutes"
echo ""

# Send requests that will fail
for i in {1..100}; do
    echo "Sending request $i/100..."
    curl -s -X POST http://localhost:8080/orders \
      -H "Content-Type: application/json" \
      -d '{
        "user_id": "1",
        "product": "fail_product",
        "quantity": 1
      }' > /dev/null
    
    # Small delay to avoid overwhelming the service
    sleep 0.1
done

echo ""
echo "✅ Error spike triggered!"
echo ""
echo "📊 Check the following:"
echo "  1. Prometheus: http://localhost:9090/alerts"
echo "     - Wait ~5 minutes for HighErrorRate alert to fire"
echo ""
echo "  2. AlertManager: http://localhost:9093"
echo "     - Alert should appear here when it fires"
echo ""
echo "  3. Grafana: http://localhost:3000/d/services"
echo "     - You should see error rate spike in the dashboard"
echo ""
echo "  4. Loki: http://localhost:3000/explore"
echo "     - Query: {service=\"order-service\"} |= \"ERROR\""
echo "     - You should see error logs"
echo ""
echo "💡 To resolve the alert, run: ./scripts/fix-error-spike.sh"
