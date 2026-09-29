# Architecture SOP — Ingestion API

> Layer 1: How Fastify receives and validates ProverReports

---

## Overview

The ingestion API is a Fastify (TypeScript) server that validates incoming ProverReports, stores them in Neon Postgres, and publishes to Redis for consensus processing.

## Endpoints

### `POST /report`
- Accepts ProverReport JSON body
- Returns `202 Accepted` on success
- Returns `400 Bad Request` on validation failure
- Returns `401 Unauthorized` on signature mismatch

## Validation Pipeline

1. **Zod Schema Validation**
   - Validates ProverReport shape against Zod schema
   - Rejects malformed requests with detailed error

2. **HMAC Signature Verification**
   - Verifies `nodeSignature` using shared `NODE_SECRET`
   - Computes HMAC-SHA256 of `nodeId + timestamp + region + targetUrl + status`
   - Rejects if signature mismatch

3. **Timestamp Validation**
   - Rejects timestamps older than 5 minutes (replay protection)
   - Rejects timestamps in the future (>30s drift)

4. **Node Registration**
   - Upserts node in `nodes` table
   - Updates `lastSeenAt` on every report

## Storage

### Neon Postgres
```sql
INSERT INTO reports (nodeId, targetUrl, region, status, latencyMs, httpStatusCode, timestamp)
VALUES ($1, $2, $3, $4, $5, $6, $7);
```

### Redis Publish
```typescript
await redis.publish("reports:raw", JSON.stringify(report));
```

## Connection Pooling

- Neon serverless driver with connection pooling
- Pool size: 5 connections (serverless-optimized)
- Connection timeout: 5s

## Error Handling

- Zod validation errors → 400 with field-level messages
- Signature mismatch → 401 "Invalid signature"
- Neon write failure → 500, log to findings.md
- Redis publish failure → 500, log but don't fail request (report still stored)
