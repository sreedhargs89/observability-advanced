# Runbook: High Error Rate

**Alert Name:** `HighErrorRate`  
**Severity:** Critical (P1)  
**Team:** Backend  
**On-Call:** Backend Team Rotation

---

## 🚨 Alert Description

This alert fires when the error rate (5xx responses) exceeds 5% for more than 5 minutes on any service.

**Threshold:** > 5% error rate  
**Duration:** 5 minutes  
**Impact:** Users experiencing failures, potential revenue loss

---

## 📊 Quick Checks

### **1. Verify the Alert** (30 seconds)

```bash
# Check current error rate in Prometheus
open http://localhost:9090/graph?g0.expr=rate(http_requests_total{status=~"5.."}[5m])%20%2F%20rate(http_requests_total[5m])

# Check which service is affected
# Look at the 'service' label in the alert
```

### **2. Check Dashboards** (1 minute)

- **Service Dashboard:** http://localhost:3000/d/services
  - Look for error rate spike
  - Check which endpoints are failing
  - Verify if it's all instances or specific ones

- **Logs Dashboard:** http://localhost:3000/explore
  - Query: `{service="<affected-service>"} |= "ERROR"`
  - Look for error messages in the last 15 minutes

### **3. Check Traces** (1 minute)

- **Jaeger:** http://localhost:16686
  - Search for traces from the affected service
  - Filter by `error=true`
  - Look at recent failed traces

---

## 🔍 Investigation Steps

### **Step 1: Identify the Root Cause** (5 minutes)

#### **A. Check Recent Deployments**
```bash
# Did we deploy recently?
git log --oneline --since="1 hour ago"

# Check deployment time
kubectl get pods -l app=<service> -o jsonpath='{.items[*].status.startTime}'
```

**If deployed in last hour → Likely cause: New deployment**

#### **B. Check Dependencies**
```bash
# Are downstream services healthy?
curl http://localhost:9090/api/v1/query?query=up{job=~".*service"}

# Check database connectivity
# Look for "connection refused" or "timeout" in logs
```

**If dependencies down → Likely cause: Downstream failure**

#### **C. Check Resource Usage**
```bash
# CPU/Memory usage
open http://localhost:3000/d/resources

# Look for:
# - CPU > 90%
# - Memory > 90%
# - Disk full
```

**If resources exhausted → Likely cause: Resource starvation**

#### **D. Check External Services**
```bash
# Payment gateway status
curl https://status.stripe.com

# Third-party API status
# Check status pages of external dependencies
```

**If external service down → Likely cause: Third-party outage**

---

## 🔧 Resolution Steps

### **Scenario 1: Bad Deployment** (Most Common)

**Symptoms:**
- Error rate spiked after deployment
- Specific error in logs (e.g., `AttributeError`, `NullPointerException`)
- Traces show errors in new code

**Resolution:**
```bash
# 1. Rollback immediately
kubectl rollout undo deployment/<service-name>

# 2. Verify rollback successful
kubectl rollout status deployment/<service-name>

# 3. Check error rate dropping
# Wait 2-3 minutes and verify in Grafana

# 4. Communicate
# Post in #incidents: "Rolled back <service> due to high error rate. Investigating root cause."
```

**Expected Time:** 5 minutes  
**Success Criteria:** Error rate < 1%

---

### **Scenario 2: Downstream Service Failure**

**Symptoms:**
- Errors like "Connection refused", "Timeout"
- Traces show failure in downstream call
- Downstream service has `up=0` in Prometheus

**Resolution:**
```bash
# 1. Identify failed service
# Check Prometheus: up{job=~".*service"} == 0

# 2. Restart the failed service
kubectl rollout restart deployment/<downstream-service>

# Or if using Docker Compose:
docker-compose restart <downstream-service>

# 3. Verify service is up
curl http://<service>:8080/health

# 4. Check error rate
# Should drop within 1-2 minutes
```

**Expected Time:** 3 minutes  
**Success Criteria:** Downstream service `up=1`, error rate < 1%

---

### **Scenario 3: Resource Exhaustion**

**Symptoms:**
- CPU > 90% or Memory > 90%
- Slow response times
- OOMKilled pods (Kubernetes)

**Resolution:**
```bash
# 1. Scale up immediately
kubectl scale deployment/<service> --replicas=6  # Double current replicas

# Or increase resources:
kubectl set resources deployment/<service> \
  --limits=cpu=2000m,memory=2Gi \
  --requests=cpu=1000m,memory=1Gi

# 2. Verify scaling
kubectl get pods -l app=<service>

# 3. Check if error rate drops
# Wait 2-3 minutes

# 4. Investigate why resources spiked
# - Traffic increase?
# - Memory leak?
# - Inefficient query?
```

**Expected Time:** 5 minutes  
**Success Criteria:** Error rate < 1%, CPU/Memory < 70%

---

### **Scenario 4: Database Issues**

**Symptoms:**
- Errors like "Too many connections", "Lock timeout"
- Slow database queries
- Connection pool exhausted

**Resolution:**
```bash
# 1. Check database connections
# Prometheus query: database_connections_active

# 2. If connection pool exhausted:
# Restart the service to reset connections
kubectl rollout restart deployment/<service>

# 3. If slow queries:
# Check slow query log
kubectl logs <db-pod> | grep "slow query"

# 4. Emergency fix:
# Increase connection pool size (temporary)
# Update config: MAX_DB_CONNECTIONS=50 (from 20)

# 5. Long-term fix:
# - Add database index
# - Optimize slow queries
# - Scale database
```

**Expected Time:** 10 minutes  
**Success Criteria:** Error rate < 1%, query time < 100ms

---

### **Scenario 5: Third-Party Outage**

**Symptoms:**
- Errors from external API (Stripe, SendGrid, etc.)
- Their status page shows outage
- Timeouts to external service

**Resolution:**
```bash
# 1. Verify it's their issue
# Check status page: https://status.<provider>.com

# 2. Enable circuit breaker (if available)
# Update config: ENABLE_CIRCUIT_BREAKER=true

# 3. Implement graceful degradation
# Example: Queue payments for later processing
# Update feature flag: PAYMENT_QUEUE_MODE=true

# 4. Communicate to users
# Update status page
# Send notification: "Payment processing delayed due to provider issue"

# 5. Monitor their status page
# Wait for resolution
```

**Expected Time:** Depends on third-party  
**Success Criteria:** Graceful degradation active, users informed

---

## 📢 Communication

### **Initial Response** (Within 2 minutes)
```
#incidents channel:
🚨 INCIDENT: High error rate on <service>
Status: Investigating
Impact: <X>% of requests failing
ETA: Investigating, update in 5 minutes
Incident Commander: @<your-name>
```

### **Update** (Every 5-10 minutes)
```
#incidents channel:
📊 UPDATE: High error rate on <service>
Root Cause: <identified cause>
Action: <what you're doing>
ETA: <expected resolution time>
```

### **Resolution**
```
#incidents channel:
✅ RESOLVED: High error rate on <service>
Root Cause: <final cause>
Resolution: <what fixed it>
Duration: <total time>
Postmortem: <link to doc>
```

---

## 📝 Post-Incident

### **1. Resolve the Alert**
- Alert should auto-resolve when error rate < 5%
- Verify in AlertManager: http://localhost:9093

### **2. Write Postmortem** (Within 24 hours)
Use template: [postmortem-template.md](../docs/05-postmortem-template.md)

**Required sections:**
- Timeline of events
- Root cause analysis
- What went well
- What went wrong
- Action items

### **3. Update Runbook** (If needed)
- Did you encounter a new scenario?
- Add it to this runbook
- Share learnings with team

### **4. Implement Preventions**
- Add monitoring to catch earlier
- Improve testing
- Add circuit breakers
- Update deployment process

---

## 🎯 Success Criteria

- [ ] Error rate < 1%
- [ ] All services `up=1`
- [ ] Response time < 200ms (P95)
- [ ] No user-facing impact
- [ ] Incident documented
- [ ] Postmortem scheduled

---

## 📚 Related Runbooks

- [Service Down](service-down.md)
- [High Latency](high-latency.md)
- [Database Issues](database-issues.md)

---

## 🔗 Useful Links

- **Grafana Dashboards:** http://localhost:3000
- **Prometheus:** http://localhost:9090
- **Jaeger:** http://localhost:16686
- **AlertManager:** http://localhost:9093
- **Incident Tracker:** https://incidents.example.com

---

## 📞 Escalation

If you can't resolve within 30 minutes:

1. **Escalate to Senior Engineer**
   - Slack: @senior-oncall
   - Phone: +1-XXX-XXX-XXXX

2. **Escalate to Engineering Manager**
   - Slack: @eng-manager
   - Phone: +1-XXX-XXX-XXXX

3. **Escalate to CTO** (Critical only)
   - Slack: @cto
   - Phone: +1-XXX-XXX-XXXX

---

**Remember:** Stay calm, follow the steps, communicate clearly, and ask for help if needed! 🚀
