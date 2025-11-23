# Module 1: Alerting & Incident Response 🚨

**Learn how to detect issues before users do and respond effectively when things go wrong.**

---

## 📚 What You'll Learn

By the end of this module, you'll be able to:
- ✅ Design effective alert rules that avoid alert fatigue
- ✅ Set up AlertManager for intelligent alert routing
- ✅ Integrate with Slack and PagerDuty for notifications
- ✅ Create incident response playbooks
- ✅ Implement on-call rotation simulation
- ✅ Practice the full incident lifecycle (detection → resolution → postmortem)

---

## 🎯 Learning Objectives

### **Beginner Level:**
- Understand the difference between symptoms vs causes
- Write basic Prometheus alert rules
- Configure AlertManager
- Send alerts to Slack

### **Intermediate Level:**
- Design alert severity levels (P0-P4)
- Implement alert routing and grouping
- Create runbooks for common issues
- Practice incident response

### **Advanced Level:**
- Avoid alert fatigue with smart thresholds
- Implement SLO-based alerting
- Build automated remediation
- Conduct blameless postmortems

---

## 🏗️ What You'll Build

```
┌─────────────────────────────────────────────────────────┐
│                  Your Microservices                      │
│         (API Gateway, User Service, Order Service)      │
└────────────┬────────────────────────────────────────────┘
             │ Metrics
             ▼
┌─────────────────────────────────────────────────────────┐
│                    Prometheus                            │
│  - Collects metrics                                     │
│  - Evaluates alert rules every 15s                      │
│  - Fires alerts when conditions are met                 │
└────────────┬────────────────────────────────────────────┘
             │ Alerts
             ▼
┌─────────────────────────────────────────────────────────┐
│                   AlertManager                           │
│  - Groups similar alerts                                │
│  - Routes alerts based on labels                        │
│  - Deduplicates and silences                           │
│  - Manages alert lifecycle                              │
└────────────┬────────────────────────────────────────────┘
             │
      ┌──────┴──────┬──────────┬──────────┐
      ▼             ▼          ▼          ▼
┌──────────┐  ┌──────────┐  ┌────────┐  ┌──────────┐
│  Slack   │  │PagerDuty │  │ Email  │  │ Webhook  │
│ #alerts  │  │ On-call  │  │ Team   │  │ Custom   │
└──────────┘  └──────────┘  └────────┘  └──────────┘
```

---

## 📋 Prerequisites

- ✅ Completed Module 0 (Core Foundation)
- ✅ Understanding of Prometheus metrics
- ✅ Basic knowledge of YAML
- 🔧 Slack workspace (optional, for notifications)
- 🔧 PagerDuty account (optional, for on-call)

---

## 🚀 Quick Start

### **1. Start the Stack**
```bash
cd 01-alerting-incident-response
docker-compose up -d
```

### **2. Access the UIs**
- **AlertManager**: http://localhost:9093
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
- **Slack Bot**: (configured in docker-compose.yml)

### **3. Trigger an Alert**
```bash
# Simulate high error rate
./scripts/trigger-error-spike.sh

# Watch the alert fire in AlertManager
open http://localhost:9093
```

### **4. Resolve the Incident**
```bash
# Follow the runbook
cat playbooks/high-error-rate.md

# Fix the issue
./scripts/fix-error-spike.sh
```

---

## 📚 Module Structure

```
01-alerting-incident-response/
├── README.md                          # This file
├── docker-compose.yml                 # Complete stack with AlertManager
├── .env.example                       # Environment variables template
│
├── alertmanager/
│   ├── alertmanager.yml              # AlertManager configuration
│   └── templates/
│       ├── slack.tmpl                # Slack message template
│       └── pagerduty.tmpl            # PagerDuty alert template
│
├── config/
│   ├── prometheus-alerts.yml        # Alert rules
│   ├── recording-rules.yml          # Recording rules for efficiency
│   └── alert-severity.yml           # Severity definitions
│
├── playbooks/
│   ├── high-error-rate.md           # Runbook for error spikes
│   ├── high-latency.md              # Runbook for slow responses
│   ├── service-down.md              # Runbook for service outages
│   └── database-issues.md           # Runbook for DB problems
│
├── scripts/
│   ├── trigger-error-spike.sh       # Simulate errors
│   ├── trigger-latency.sh           # Simulate slow responses
│   ├── trigger-outage.sh            # Simulate service down
│   └── fix-*.sh                     # Resolution scripts
│
└── docs/
    ├── 01-alert-design.md           # How to design good alerts
    ├── 02-alertmanager-setup.md     # AlertManager configuration
    ├── 03-notification-channels.md  # Slack, PagerDuty, Email
    ├── 04-incident-response.md      # Incident management
    └── 05-postmortem-template.md    # Blameless postmortem
```

---

## 🎓 Learning Path

### **Day 1: Alert Design & Setup** (3-4 hours)

**Morning:**
1. Read [Alert Design Principles](docs/01-alert-design.md)
2. Understand the difference between symptoms and causes
3. Learn about alert severity levels

**Afternoon:**
1. Set up AlertManager
2. Write your first alert rule
3. Test alert firing and resolution

**Hands-on Exercise:**
- Create an alert for high error rate (>5%)
- Trigger it manually
- Watch it fire and resolve

---

### **Day 2: Notification Channels** (3-4 hours)

**Morning:**
1. Configure Slack integration
2. Set up email notifications
3. (Optional) Integrate PagerDuty

**Afternoon:**
1. Test different notification channels
2. Configure alert routing
3. Set up alert grouping

**Hands-on Exercise:**
- Route P0/P1 alerts to PagerDuty
- Route P2/P3 alerts to Slack
- Route P4 alerts to email

---

### **Day 3: Incident Response** (3-4 hours)

**Morning:**
1. Learn incident response lifecycle
2. Create runbooks for common issues
3. Practice incident simulation

**Afternoon:**
1. Run full incident drill
2. Write a postmortem
3. Implement improvements

**Hands-on Exercise:**
- Simulate a production outage
- Follow the runbook to resolve it
- Write a blameless postmortem

---

## 🔥 Real-World Scenarios

### **Scenario 1: High Error Rate**
```yaml
# Alert fires when error rate > 5% for 5 minutes
- alert: HighErrorRate
  expr: |
    rate(http_requests_total{status=~"5.."}[5m])
    / rate(http_requests_total[5m]) > 0.05
  for: 5m
  labels:
    severity: critical
    team: backend
  annotations:
    summary: "High error rate on {{ $labels.service }}"
    description: "Error rate is {{ $value | humanizePercentage }}"
    runbook: "https://runbooks.example.com/high-error-rate"
```

**What happens:**
1. ⚠️ Alert fires in Prometheus
2. 📢 AlertManager sends to Slack #alerts
3. 📟 PagerDuty pages on-call engineer
4. 📖 Engineer follows runbook
5. ✅ Issue resolved, alert auto-resolves
6. 📝 Postmortem written

---

### **Scenario 2: Service Down**
```yaml
- alert: ServiceDown
  expr: up{job="order-service"} == 0
  for: 1m
  labels:
    severity: critical
    team: backend
  annotations:
    summary: "{{ $labels.job }} is down"
    description: "Service has been down for more than 1 minute"
```

**What happens:**
1. 🚨 Immediate page to on-call (P0)
2. 🔍 Check service logs in Loki
3. 🔎 View recent traces in Jaeger
4. 🔧 Restart service or rollback
5. ✅ Service recovers
6. 📊 Update SLO dashboard

---

### **Scenario 3: High Latency**
```yaml
- alert: HighLatency
  expr: |
    histogram_quantile(0.95,
      rate(http_request_duration_seconds_bucket[5m])
    ) > 1.0
  for: 10m
  labels:
    severity: warning
    team: backend
  annotations:
    summary: "High latency on {{ $labels.service }}"
    description: "P95 latency is {{ $value }}s (threshold: 1s)"
```

**What happens:**
1. ⚠️ Warning alert to Slack
2. 📊 Check Grafana dashboards
3. 🔍 Identify slow endpoint in Jaeger
4. 🐛 Find slow database query
5. ⚡ Optimize query or add index
6. ✅ Latency returns to normal

---

## 📊 Alert Severity Levels

| Level | Name | Response Time | Notification | Examples |
|-------|------|--------------|--------------|----------|
| **P0** | Critical | Immediate | PagerDuty + Slack + Email | Service down, data loss |
| **P1** | High | 15 minutes | PagerDuty + Slack | High error rate, security breach |
| **P2** | Medium | 1 hour | Slack + Email | High latency, degraded performance |
| **P3** | Low | 4 hours | Slack | Approaching thresholds, warnings |
| **P4** | Info | Next business day | Email | Informational, metrics |

---

## 🎯 Best Practices

### **DO:**
✅ Alert on symptoms, not causes  
✅ Make alerts actionable  
✅ Include runbook links  
✅ Use appropriate severity levels  
✅ Test alerts regularly  
✅ Review and update alerts  
✅ Write blameless postmortems  

### **DON'T:**
❌ Alert on everything  
❌ Use vague descriptions  
❌ Set thresholds too low  
❌ Ignore alert fatigue  
❌ Skip postmortems  
❌ Blame individuals  
❌ Create alerts without runbooks  

---

## 🧪 Exercises

### **Exercise 1: Create Your First Alert**
Create an alert that fires when CPU usage > 80% for 5 minutes.

**Solution:** [docs/exercises/01-cpu-alert.md](docs/exercises/01-cpu-alert.md)

---

### **Exercise 2: Alert Routing**
Route critical alerts to PagerDuty and warnings to Slack.

**Solution:** [docs/exercises/02-alert-routing.md](docs/exercises/02-alert-routing.md)

---

### **Exercise 3: Incident Simulation**
Simulate a production outage and practice the full incident response lifecycle.

**Solution:** [docs/exercises/03-incident-drill.md](docs/exercises/03-incident-drill.md)

---

## 📈 Success Metrics

After completing this module, you should be able to:

- [ ] Design alerts that detect real issues
- [ ] Avoid alert fatigue (< 5% false positives)
- [ ] Respond to incidents in < 5 minutes
- [ ] Write effective runbooks
- [ ] Conduct blameless postmortems
- [ ] Reduce MTTR (Mean Time To Resolution)

---

## 🔗 Additional Resources

- [Google SRE Book - Monitoring](https://sre.google/sre-book/monitoring-distributed-systems/)
- [Prometheus Alerting Best Practices](https://prometheus.io/docs/practices/alerting/)
- [PagerDuty Incident Response](https://response.pagerduty.com/)
- [Atlassian Incident Management](https://www.atlassian.com/incident-management)

---

## 🚀 Next Steps

After completing this module:

1. **Module 2: Chaos Engineering** - Test your alerts by breaking things
2. **Module 3: SLO/SLI Monitoring** - Alert based on error budgets
3. **Module 8: Multi-Environment** - Different alerts for dev/staging/prod

---

## 🤝 Need Help?

- 📖 Check the [documentation](docs/)
- 🐛 Review [troubleshooting guide](docs/troubleshooting.md)
- 💬 Open an issue on GitHub
- 📧 Ask in the discussion forum

---

**Let's build production-grade alerting!** 🚨

**Ready to start?**
```bash
docker-compose up -d
open http://localhost:9093
```
