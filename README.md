# Upwatch

**Decentralized, trustless website uptime monitoring with on-chain SLA enforcement.**

Upwatch replaces single-provider trust with a network of distributed prover agents that reach consensus on outage events before recording them on-chain. No single agent can fabricate downtime -- outages are only confirmed when a quorum of independent nodes across multiple regions agree.

## How It Works

```
 Distributed Agents          Ingestion API          Consensus Engine
 (Python, multi-region)      (Fastify, TS)          (BullMQ + Redis)
        │                          │                        │
        │  HMAC-SHA256 signed      │                        │
        │  reports every 15s       │                        │
        ├─────────────────────────►│    pub/sub "reports:raw"│
        │                          ├───────────────────────►│
        │                          │                        │
        │                          │   Sliding window       │
        │                          │   60%+ quorum check    │
        │                          │                        │
        │                          │                        ▼
        │                          │               Blockchain Layer
        │                          │               (Solidity / Sepolia)
        │                          │                        │
        │                          │                  OutageLedger
        │                          │                  SLAEscrow
        │                          │                        │
        │                          │                        ▼
        │                          │                  Dashboard
        │                          │                  (Next.js)
        │                          │                  SSE live feed
        │                          │                  Global heatmap
```

1. **Agents** deploy across regions and ping monitored targets every 15 seconds
2. **Reports** are signed with HMAC-SHA256 and submitted to the ingestion API
3. **Consensus** engine aggregates reports in a 60-second sliding window -- if 60%+ of active nodes in a region confirm DOWN, the outage is CONFIRMED
4. **Confirmed outages** are recorded on Ethereum Sepolia via the `OutageLedger` contract
5. **SLA contracts** can automatically trigger penalties for verified outages via `SLAEscrow`
6. **Dashboard** displays real-time outages through SSE and a global heatmap

## Architecture

Upwatch consists of five layers:

| Layer | Directory | Description |
|-------|-----------|-------------|
| **Prover Agent** | `apps/agent/` | Python async pinger with NTP-synced timestamps, HMAC signing, SQLite local queue with backoff retry |
| **Ingestion API** | `apps/api/` | Fastify 5 server that validates reports, verifies HMAC signatures, writes to Neon Postgres, publishes to Redis |
| **Consensus Engine** | `apps/consensus/` | BullMQ worker consuming from Redis pub/sub. Sliding window aggregation with filters (silent node, rate limit, region blackout). Writes confirmed outages to DB and queues blockchain transactions |
| **Smart Contracts** | `apps/contracts/` | Solidity 0.8.24 contracts on Ethereum Sepolia. `OutageLedger` records/resolves outages. `SLAEscrow` manages escrow deposits and automatic penalty triggers |
| **Dashboard** | `apps/dashboard/` | Next.js 16 App Router dashboard with Clerk auth, RainbowKit wallet connect, Leaflet heatmap, real-time SSE outage feed, target management |

## Tech Stack

| Category | Technology |
|----------|------------|
| Agent | Python, httpx, ntplib, Redis, SQLite |
| API | TypeScript, Fastify 5, Zod, Neon Postgres, ioredis |
| Consensus | TypeScript, BullMQ, Redis, viem |
| Contracts | Solidity 0.8.24, Hardhat, ethers.js |
| Dashboard | TypeScript, Next.js 16, React 19, Tailwind CSS, Radix UI, Leaflet |
| Auth | Clerk (SSO + session), RainbowKit (wallet connect) |
| Database | Neon Postgres (serverless), Redis (Upstash / local Docker) |
| Blockchain | Ethereum Sepolia testnet, Alchemy / Infura RPC |

## Project Structure

```
upwatch/
├── apps/
│   ├── agent/                # Python prover agent
│   │   ├── main.py           # Orchestrator: pinger → signer → POST → queue
│   │   └── core/
│   │       ├── pinger.py     # Async HTTP ping with httpx
│   │       ├── signer.py     # HMAC-SHA256 report signing
│   │       ├── queue.py      # SQLite local queue with exponential backoff
│   │       └── config.py     # Dynamic target config (API + Redis pub/sub)
│   │
│   ├── api/                  # Fastify 5 ingestion API
│   │   └── src/
│   │       ├── server.ts
│   │       ├── routes/       # /report, /targets, /health, /stats
│   │       ├── db/           # Neon client + CRUD
│   │       ├── queue/        # Redis publisher to "reports:raw"
│   │       ├── plugins/      # Clerk auth hook
│   │       └── schemas/      # Zod validation schemas
│   │
│   ├── consensus/            # Consensus engine
│   │   └── src/
│   │       ├── worker.ts     # BullMQ consumer, orchestrator
│   │       ├── aggregator.ts # Redis sorted set sliding window
│   │       ├── filters/      # silentNode, rateLimit, regionBlackout
│   │       └── blockchain/   # Oracle client + retry worker
│   │
│   ├── contracts/            # Solidity smart contracts
│   │   ├── contracts/
│   │   │   ├── OutageLedger.sol
│   │   │   └── SLAEscrow.sol
│   │   ├── test/             # 13 contract tests
│   │   └── scripts/          # Deploy script
│   │
│   └── dashboard/            # Next.js 16 dashboard
│       ├── app/
│       │   ├── page.tsx      # Stats, heatmap, outage table, live feed
│       │   ├── targets/      # Target management CRUD
│       │   ├── sign-in/      # Clerk auth page
│       │   ├── api/live/     # SSE endpoint
│       │   └── components/   # Heatmap, OutageTable, LiveFeed, Navbar, etc.
│       └── middleware.ts     # Clerk auth middleware
│
├── architecture/             # Architecture design documents
├── scripts/
│   └── init.sql              # Full database schema (5 tables)
├── infra/
│   └── neon/                 # DB migrations
├── tools/                    # Verification scripts (Neon, Redis, RPC)
├── docker-compose.yml        # Local Redis + Postgres
├── .env.example              # Environment variable template
├── claude.md                 # Project constitution (schemas, rules, invariants)
└── task_plan.md              # Sprint checklist
```

## Getting Started

### Prerequisites

- **Node.js** >= 18
- **Python** >= 3.10
- **Docker** & Docker Compose
- **Neon Postgres** account ([neon.tech](https://neon.tech))
- **Alchemy** or **Infura** RPC endpoint for Ethereum Sepolia
- **Clerk** account for authentication ([clerk.com](https://clerk.com))

### 1. Clone & Install

```bash
git clone https://github.com/dhanush-adi/Upwatch.git
cd Upwatch

# Copy environment template
cp .env.example .env
# Edit .env with your credentials
```

### 2. Start Infrastructure

```bash
# Start Redis + Postgres locally
docker-compose up -d

# Or use cloud services (Upstash Redis, Neon Postgres) -- configure .env accordingly
```

### 3. Install Dependencies

```bash
# API
cd apps/api && npm install && cd ../..

# Consensus
cd apps/consensus && npm install && cd ../..

# Dashboard
cd apps/dashboard && npm install && cd ../..

# Contracts
cd apps/contracts && npm install && cd ../..

# Agent
cd apps/agent && pip install -r requirements.txt && cd ../..
```

### 4. Run Services

```bash
# API (port 3001)
cd apps/api && npm run dev

# Consensus Engine
cd apps/consensus && npm run dev

# Dashboard (port 3000)
cd apps/dashboard && npm run dev

# Prover Agent
cd apps/agent && python main.py
```

### 5. Deploy Contracts (Optional)

```bash
cd apps/contracts
npx hardhat compile
npx hardhat test
npm run deploy:sepolia
```

## Smart Contracts

### OutageLedger

Records confirmed outages on Ethereum Sepolia. Only the oracle wallet (deployer) can write records.

- `recordOutage()` -- Store a consensus-verified outage on-chain
- `resolveOutage()` -- Mark an outage as resolved with timestamp
- `updateOracle()` -- Rotate the oracle address
- Duplicate prevention via `AlreadyRecorded` revert

### SLAEscrow

Manages escrow deposits and automatic penalty triggers for SLA breaches.

- `depositEscrow()` -- Deposit ETH to cover a target URL with SLA guarantees
- `triggerPenalty()` -- Oracle triggers penalty (validates outage exists in OutageLedger first)
- `withdraw()` -- Withdraw remaining escrow balance
- Penalties scale with `penaltyPerHour * durationHours`

## Configuration

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Neon Postgres connection string |
| `REDIS_URL` | Redis URL (local or Upstash) |
| `ALCHEMY_RPC_URL` | Ethereum Sepolia RPC endpoint |
| `DEPLOYER_PRIVATE_KEY` | Oracle wallet private key (no 0x prefix) |
| `NODE_SECRET` | Shared secret for HMAC report signing |
| `AGENT_REGION` | Region identifier for this agent instance |
| `AGENT_TARGETS` | Comma-separated list of URLs to monitor |
| `CONSENSUS_THRESHOLD` | Quorum required to confirm outage (default: 0.6 = 60%) |

See [`.env.example`](.env.example) for the full list.

## Key Design Decisions

- **Consensus before blockchain** -- Outages are only recorded on-chain after multi-node agreement. A single agent can never trigger a false positive.
- **HMAC-SHA256 report signing** -- Every report is cryptographically signed. The API uses `timingSafeEqual` for constant-time comparison to prevent timing attacks.
- **Redis pub/sub for real-time processing** -- The consensus engine subscribes to report streams via Redis, not polling.
- **Sliding window aggregation** -- Reports are aggregated in a 60-second window with automatic expiry trimming.
- **Three-layer false positive filtering** -- Silent node exclusion (>5min), rate limiting (15s per node+target), and region blackout detection.
- **NTP-synced timestamps** -- Agents never trust their own clock; they sync with pool.ntp.org.
- **Oracle-only contract access** -- Both contracts use `onlyOracle` modifier for write protection.
- **Async blockchain writes** -- Non-blocking with BullMQ retry and exponential backoff.

## License

MIT
