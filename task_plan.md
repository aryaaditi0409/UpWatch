# Task Plan — B.L.A.S.T. Protocol

> Status markers: [ ] TODO | [~] IN PROGRESS | [x] DONE

---

## Phase 0: Foundation

- [x] Create claude.md (Project Constitution)
- [x] Create task_plan.md (this file)
- [x] Create findings.md
- [x] Create progress.md
- [ ] User confirms data schemas in claude.md

---

## Phase 1: Verification Scripts

- [ ] tools/verify_neon.py — Connect to Neon, run SELECT NOW()
- [ ] tools/verify_redis.py — PING + pub/sub test on "outages:live"
- [ ] tools/verify_rpc.py — Fetch latest block, check deployer balance
- [ ] All 3 scripts return green

---

## Phase 2: Architecture SOPs

- [ ] architecture/01_prover_agent.md — Agent design doc
- [ ] architecture/02_ingestion_api.md — API design doc
- [ ] architecture/03_consensus_engine.md — Consensus design doc
- [ ] architecture/04_blockchain_layer.md — Oracle + retry design doc
- [ ] architecture/05_dashboard.md — Dashboard design doc

---

## Sprint 1: Agent + Ingestion API

### Agent (Python)
- [ ] apps/agent/core/pinger.py — Async ping loop with httpx
- [ ] apps/agent/core/signer.py — HMAC-SHA256 signing, key generation
- [ ] apps/agent/core/queue.py — SQLite local queue with backoff
- [ ] apps/agent/main.py — Orchestrator: pinger → signer → POST
- [ ] apps/agent/requirements.txt
- [ ] apps/agent/.env.example

### Ingestion API (Fastify/TypeScript)
- [ ] apps/api/package.json
- [ ] apps/api/tsconfig.json
- [ ] apps/api/src/server.ts — Fastify server setup
- [ ] apps/api/src/routes/report.ts — POST /report handler
- [ ] apps/api/src/db/neon.ts — Neon serverless client
- [ ] apps/api/src/queue/publisher.ts — ioredis publisher
- [ ] apps/api/src/schemas/proverReport.ts — Zod schema
- [ ] apps/api/.env.example

### Sprint 1 Gate
- [ ] Run agent against live URL
- [ ] Confirm report in Neon reports table
- [ ] Confirm message on Redis "reports:raw" channel
- [ ] **GATE: Do not proceed until passed**

---

## Sprint 2: Consensus Engine

### Worker
- [ ] apps/consensus/package.json
- [ ] apps/consensus/tsconfig.json
- [ ] apps/consensus/src/worker.ts — BullMQ worker
- [ ] apps/consensus/src/aggregator.ts — Redis sorted set sliding window
- [ ] apps/consensus/src/publisher.ts — Publish to "outages:live"

### Filters
- [ ] apps/consensus/src/filters/silentNode.ts — Exclude silent >5m
- [ ] apps/consensus/src/filters/rateLimit.ts — 15s per node+target
- [ ] apps/consensus/src/filters/regionBlackout.ts — REGION_BLACKOUT
- [ ] apps/consensus/src/db/neon.ts — Read nodes, write outages
- [ ] apps/consensus/.env.example

### Sprint 2 Gate
- [ ] Simulate 5 nodes reporting DOWN → CONFIRMED event
- [ ] Simulate 1 node reporting DOWN → INCONCLUSIVE logged
- [ ] **GATE: Do not proceed until passed**

---

## Sprint 3: Blockchain + Dashboard

### Smart Contracts
- [ ] apps/contracts/package.json
- [ ] apps/contracts/hardhat.config.ts
- [ ] apps/contracts/contracts/OutageLedger.sol
- [ ] apps/contracts/contracts/SLAEscrow.sol
- [ ] apps/contracts/test/OutageLedger.test.ts
- [ ] apps/contracts/test/SLAEscrow.test.ts
- [ ] apps/contracts/scripts/deploy.ts

### Oracle
- [ ] apps/consensus/src/blockchain/oracle.ts — viem wallet client
- [ ] apps/consensus/src/blockchain/retryWorker.ts — Poll pending_writes

### Dashboard (Next.js 15)
- [ ] apps/dashboard/package.json
- [ ] apps/dashboard/next.config.js
- [ ] apps/dashboard/tailwind.config.js
- [ ] apps/dashboard/app/layout.tsx — Root layout with dark theme
- [ ] apps/dashboard/app/page.tsx — Main dashboard page
- [ ] apps/dashboard/app/api/live/route.ts — SSE endpoint
- [ ] apps/dashboard/app/components/Heatmap.tsx — react-leaflet
- [ ] apps/dashboard/app/components/OutageTable.tsx — Neon fallback
- [ ] apps/dashboard/app/components/LiveFeed.tsx — SSE consumer
- [ ] apps/dashboard/app/components/ConnectionStatus.tsx — Dot indicator
- [ ] apps/dashboard/.env.example

### Sprint 3 Gate
- [ ] Deploy contracts to Base Sepolia
- [ ] Record outage on-chain, verify OutageRecorded event
- [ ] Dashboard shows live heatmap + outage table
- [ ] SSE reconnects on disconnect with backoff
- [ ] Present dashboard to user for feedback
- [ ] **GATE: Do not proceed until passed**

---

## Phase 4: Polish + Deployment

- [ ] Dashboard dark theme by default
- [ ] Connection status indicator (green/red dot)
- [ ] "Showing cached data" amber badge
- [ ] Responsive mobile layout
- [ ] Agent CLI output: colored, timestamped
- [ ] docker-compose.yml (Redis + local Postgres)
- [ ] Deploy API + Consensus to Railway/Render
- [ ] Deploy Dashboard to Vercel
- [ ] Deploy contracts, save addresses
- [ ] Update claude.md with production values
