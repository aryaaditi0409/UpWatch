# Architecture SOP — Consensus Engine

> Layer 1: How BullMQ worker aggregates reports

---

## Overview

The consensus engine is a BullMQ worker that consumes raw reports from Redis, aggregates them using sliding windows, and produces confirmed consensus events.

## Data Flow

```
Redis "reports:raw" channel
  → BullMQ worker receives
  → Apply filters
  → Add to Redis sorted set (region:targetUrl)
  → Aggregate sliding window (60s)
  → If CONFIRMED → publish to "outages:live" + enqueue blockchain write
  → If INCONCLUSIVE → log only
```

## Sliding Window Aggregation

### Redis Sorted Set Structure
- Key: `window:{region}:{targetUrl}`
- Score: timestamp (unix seconds)
- Member: JSON of report

### Aggregation Logic
```typescript
const now = Math.floor(Date.now() / 1000);
const windowStart = now - WINDOW_SECONDS; // 60s

// Remove expired entries
await redis.zremrangebyscore(key, 0, windowStart);

// Get active window
const reports = await redis.zrangebyscore(key, windowStart, now);

// Count DOWN/TIMEOUT reports
const downCount = reports.filter(r => r.status === "DOWN" || r.status === "TIMEOUT").length;
const totalActive = await getActiveNodesInRegion(region);

const consensusScore = downCount / totalActive;
```

## Consensus Threshold

- **CONFIRMED**: `consensusScore >= 0.6` (≥60% of active nodes)
- **INCONCLUSIVE**: Window closes with `consensusScore < 0.6`
- **RESOLVED**: Target returns UP for 3 consecutive checks

## False Positive Filters

### 1. Silent Node Filter (`filters/silentNode.ts`)
- Queries `nodes` table for `lastSeenAt`
- Excludes nodes silent for >5 minutes
- Marks node `isActive = false` if silent >5 minutes

### 2. Rate Limit Filter (`filters/rateLimit.ts`)
- Redis key: `ratelimit:{nodeId}:{targetUrl}`
- TTL: 15 seconds
- Rejects duplicate reports within window

### 3. Region Blackout Filter (`filters/regionBlackout.ts`)
- If `activeNodesInRegion === 0` → emit `REGION_BLACKOUT` event
- Do not process as standard outage
- Special handling: alert on dashboard but don't trigger SLA

## Job Processing

```typescript
const worker = new Worker("reports:raw", async (job) => {
  const report = job.data;

  // Apply filters
  if (await isSilentNode(report.nodeId)) return;
  if (await isRateLimited(report.nodeId, report.targetUrl)) return;

  // Add to window
  await addToWindow(report);

  // Aggregate
  const consensus = await aggregateWindow(report.region, report.targetUrl);

  if (consensus.status === "CONFIRMED") {
    await publishOutage(consensus);
    await enqueueBlockchainWrite(consensus);
    await mirrorToNeon(consensus);
  }
}, { connection: redisConnection });
```

## Outputs

### CONFIRMED
- Publish to Redis channel `outages:live`
- Insert into Neon `outages` table
- Enqueue BullMQ job for blockchain write

### INCONCLUSIVE
- Log to findings.md
- No further action

### REGION_BLACKOUT
- Publish to Redis channel `outages:live` with type `REGION_BLACKOUT`
- Log to findings.md
- No blockchain write
