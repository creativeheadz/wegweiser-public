# Health Scoring System

The hierarchical health scoring system is the core of Wegweiser's intelligence layer.

## Overview

Health scores provide a quantitative measure of system health at every level:
- **Device Level** - Individual machine health (1-100)
- **Group Level** - Aggregate of device scores
- **Organization Level** - Aggregate of group scores
- **Tenant Level** - Aggregate of organization scores

## Scoring Methodology

### Individual Analyzers
Each analyzer produces a health score (1-100) based on specific criteria:

**Security Analyzer**
- Unauthorized access attempts
- Privilege escalation events
- Suspicious activities
- Failed login patterns

**System Events Analyzer**
- Hardware issues
- Driver problems
- Boot performance
- System stability

**Driver Analysis**
- Outdated drivers
- Unsigned drivers
- Problematic drivers
- Driver conflicts

**Performance Analyzer**
- CPU utilization
- Memory usage
- Disk I/O
- Network performance

**Application Stability**
- Application crashes
- Crash frequency
- Problematic applications
- Stability trends

### Score Calculation

Each analyzer:
1. Collects relevant data
2. Analyzes patterns and anomalies
3. Generates AI-powered insights
4. Produces health score (1-100)
5. Stores results with timestamp

**Score Interpretation:**
- **90-100** - Excellent (no action needed)
- **70-89** - Good (monitor for changes)
- **50-69** - Fair (review recommendations)
- **30-49** - Poor (action recommended)
- **1-29** - Critical (immediate action needed)

## Aggregation

### Device Health
```
Device Health = Average(All Analyzer Scores)
```

Example:
- Security: 85
- System Events: 72
- Drivers: 88
- Performance: 91
- Stability: 79

**Device Health = (85 + 72 + 88 + 91 + 79) / 5 = 83**

### Group Health
```
Group Health = Average(All Device Scores in Group)
```

### Organization Health
```
Org Health = Average(All Group Scores in Organization)
```

### Tenant Health
```
Tenant Health = Average(All Organization Scores in Tenant)
```

## Recommendations

### Generation
- AI analyzes low-scoring areas
- Generates prioritized recommendations
- Includes severity level
- Provides remediation steps

### Prioritization
1. **Critical** - Immediate security or stability issues
2. **High** - Performance or reliability concerns
3. **Medium** - Optimization opportunities
4. **Low** - Best practices and improvements

### Cascade
Recommendations cascade up the hierarchy:
- Device recommendations visible at device level
- Group recommendations aggregate device issues
- Organization recommendations show client-wide patterns
- Tenant recommendations highlight cross-client trends

## Historical Tracking

### Time Series Data
- Scores stored with timestamp
- Historical trends visible
- Pattern detection over time
- Anomaly identification

### Trend Analysis
- Score improvement/degradation
- Seasonal patterns
- Event correlation
- Predictive insights

## AI Integration

### Context-Aware Analysis
- Historical context included in AI prompts
- Previous recommendations considered
- Patterns identified across time
- Actionable insights generated

### Multiple AI Providers
- Azure OpenAI
- OpenAI
- Anthropic Claude
- Ollama (on-premises)

### Customization
- Configurable prompts per analyzer
- Tenant-specific thresholds
- Custom scoring weights
- Industry-specific rules

## Implementation

### Task Processing
1. Agent collects data
2. Data stored in DeviceMetadata
3. Celery worker picks up pending analyses
4. Analyzer validates data and billing
5. Historical context gathered
6. AI analysis performed
7. Health score calculated
8. Results stored
9. Recommendations generated

### Database Schema
- `HealthScore` - Individual scores
- `HealthScoreHistory` - Historical tracking
- `Recommendation` - Generated recommendations
- `DeviceMetadata` - Raw collected data

### Scheduling
- Configurable per analyzer
- Automatic retry on failure
- Billing integration
- Performance optimization

## Monitoring

### Dashboard Metrics
- Current health scores
- Score trends
- Recommendation status
- Analysis coverage

### Alerts
- Score drops below threshold
- Critical recommendations generated
- Analysis failures
- Billing issues

## Best Practices

### For MSPs
- Review health scores regularly
- Act on critical recommendations
- Track score trends over time
- Use for client reporting

### For Developers
- Ensure analyzers produce meaningful scores
- Include historical context in analysis
- Generate actionable recommendations
- Test scoring logic thoroughly

## Related Documentation

- [Analysis Framework](./core-analysis-framework.md)
- [Multi-Entity Chat System](./core-multi-entity-chat.md)
- [Data Processing](./data-eventlog-processing.md)

---

**Next:** Review [Analysis Framework](./core-analysis-framework.md) for implementation details.

