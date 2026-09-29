# Findings — API Quirks, Constraints, Discoveries

> Log every library constraint, API quirk, or unexpected behavior here.
> Updated during build as new discoveries are made.

---

## Template Entry

```
### [DATE] — [COMPONENT]
**Finding**: Short description
**Impact**: What this affects
**Workaround**: How we handle it
**Status**: OPEN | RESOLVED | WONTFIX
```

---

## Entries

*(No entries yet — will be populated during build)*

---

## Known Constraints (Pre-Build)

### Neon Serverless Postgres
- Connection pooling may behave differently in edge/serverless environments
- Cold start latency on first query after idle

### Redis (Upstash / Local Docker)
- Upstash free tier: 10K commands/day
- Local Docker for dev, Upstash for prod
- Pub/sub requires persistent connection

### ETH Sepolia RPC
- Rate limits vary by provider (Alchemy vs Infura)
- Testnet ETH required for gas
- Transaction confirmation latency: 2-15 seconds

### Hardhat
- Requires Node.js 18+
- Contract compilation uses solc
- Gas estimation can fail on first deploy

### Next.js 15
- App Router by default
- Server components for Neon reads
- Client components for SSE consumers
- Edge runtime for /api/live route

### httpx (Python)
- Async HTTP client
- Timeout handling returns exceptions, not null latency
- Need to catch and convert to TIMEOUT status

### BullMQ
- Requires Redis connection
- Worker concurrency configurable
- Job retry with exponential backoff built-in

### viem
- Wallet client for contract interactions
- Gas estimation can fail — need try/catch
- Transaction receipt polling required

### [2026-03-20 17:29:20 UTC] — Neon Postgres
**Finding**: DATABASE_URL not set
**Status**: OPEN

### [2026-03-20 17:29:21 UTC] — Redis
**Finding**: Redis PING + pub/sub OK
**Status**: RESOLVED

### [2026-03-20 17:29:21 UTC] — ETH Sepolia RPC
**Finding**: No RPC URL configured
**Status**: OPEN

### [2026-03-20 17:29:31 UTC] — ETH Sepolia RPC
**Finding**: RPC OK. Block: 10485263. Balance check skipped.
**Status**: RESOLVED

### [2026-03-20 17:29:33 UTC] — Neon Postgres
**Finding**: Neon connection OK. Server time: 2026-03-20 17:29:32.953861+00:00. Tables: ['nodes', 'reports', 'outages', 'pending_chain_writes', 'sla_contracts']
**Status**: RESOLVED

### [2026-03-20 17:30:21 UTC] — ETH Sepolia RPC
**Finding**: RPC OK. Block: 10485267. Balance: 6.709372 ETH
**Status**: RESOLVED

---

## Verification Summary (2026-03-20)

| Service | Status | Details |
|---------|--------|---------|
| Neon Postgres | GREEN | Connected, 5 tables exist |
| Redis (Upstash) | GREEN | PING + pub/sub verified |
| ETH Sepolia RPC | GREEN | Chain 11155111, wallet 6.709 ETH |

**All 3 verification scripts passed. Ready to proceed to Sprint 1 testing.**

---

## Sprint 1 Discoveries (2026-03-20)

### [2026-03-20 17:35:11 UTC] — Neon Postgres
**Finding**: Existing database had incompatible schema (snake_case columns, different types)
**Impact**: Reports table had foreign key to nodes.id instead of nodes.nodeId, causing 500 errors
**Workaround**: Dropped and recreated all tables with our schema
**Status**: RESOLVED

### [2026-03-20 17:35:12 UTC] — Agent / API
**Finding**: Agent generates own secret, but API verifies with NODE_SECRET from .env
**Impact**: All reports rejected with 401 "Invalid signature"
**Workaround**: Updated agent signer.py to use NODE_SECRET from environment if set
**Status**: RESOLVED

### [2026-03-20 17:36:39 UTC] — Agent
**Finding**: Python output buffering hides agent logs in bash
**Impact**: Agent runs but no output visible
**Workaround**: Use `python3 -u main.py` for unbuffered output
**Status**: RESOLVED

### Sprint 1 Gate: PASSED
- Agent pings 2 targets every 15s
- Reports stored in Neon (10 reports verified)
- Reports published to Redis `reports:raw` channel
- API returns 202 Accepted
