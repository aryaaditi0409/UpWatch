# Project Constitution — LAW

> This file defines all schemas, rules, and invariants.
> **Never modify without flagging to the user first.**

---

## Data Schemas

### ProverReport (Input)

```typescript
ProverReport {
  nodeId:         string     // UUID, generated on first agent install
  nodeSignature:  string     // HMAC-SHA256 of payload using node secret
  timestamp:      string     // ISO8601, NTP-synced
  region:         string     // e.g. "asia-south-1"
  targetUrl:      string     // e.g. "https://api.stripe.com"
  latencyMs:      number | null  // null = complete timeout
  status:         "UP" | "DOWN" | "TIMEOUT" | "DEGRADED"
  httpStatusCode: number | null
}
```

### ConsensusEvent (Intermediate)

```typescript
ConsensusEvent {
  outageId:           string   // UUID
  targetUrl:          string
  region:             string
  startTimestamp:     string   // ISO8601
  detectedAt:         string   // ISO8601
  affectedNodeCount:  number
  totalNodesInRegion: number
  consensusScore:     number   // 0.0 to 1.0
  status:             "CONFIRMED" | "INCONCLUSIVE" | "RESOLVED"
}
```

### OnChainOutageRecord (Output)

```solidity
OnChainOutageRecord {
  outageId:       bytes32
  targetUrl:      string
  region:         string
  startTimestamp: uint256   // unix
  consensusScore: uint8     // 0-100
  affectedNodes:  uint16
  resolvedAt:     uint256   // 0 if still active
}
```

---

## Database Tables (Neon Postgres)

### `nodes`
| Column      | Type        | Notes                          |
|-------------|-------------|--------------------------------|
| nodeId      | UUID (PK)   | Generated on first agent install |
| region      | VARCHAR     | e.g. "asia-south-1"            |
| lastSeenAt  | TIMESTAMPTZ | Updated on every report        |
| isActive    | BOOLEAN     | true if lastSeenAt > now()-5m  |

### `reports`
| Column        | Type        | Notes                        |
|---------------|-------------|------------------------------|
| id            | BIGSERIAL PK| Auto-increment               |
| nodeId        | UUID (FK)   | References nodes             |
| targetUrl     | TEXT        | Monitored URL                |
| region        | VARCHAR     | Agent region                 |
| status        | VARCHAR     | UP/DOWN/TIMEOUT/DEGRADED     |
| latencyMs     | INTEGER     | NULL if timeout              |
| httpStatusCode| INTEGER     | NULL if timeout              |
| timestamp     | TIMESTAMPTZ | NTP-synced agent time        |

### `outages`
| Column            | Type        | Notes                      |
|-------------------|-------------|----------------------------|
| outageId          | UUID (PK)   | Consensus event ID         |
| targetUrl         | TEXT        | Monitored URL              |
| region            | VARCHAR     | Affected region            |
| startTimestamp     | TIMESTAMPTZ | When outage started        |
| consensusScore    | DECIMAL     | 0.0 to 1.0                |
| affectedNodeCount | INTEGER     | Nodes reporting DOWN       |
| onChainTxHash     | TEXT        | NULL if pending/failed     |
| status            | VARCHAR     | CONFIRMED/RESOLVED/PENDING |

### `sla_contracts`
| Column         | Type        | Notes                     |
|----------------|-------------|---------------------------|
| id             | BIGSERIAL PK| Auto-increment            |
| clientAddress  | TEXT        | Ethereum address          |
| targetUrl      | TEXT        | SLA-covered URL           |
| escrowAmount   | BIGINT      | Wei amount                |
| penaltyPerHour | BIGINT      | Wei per hour of outage    |
| createdAt      | TIMESTAMPTZ | Contract creation time    |

### `pending_chain_writes`
| Column      | Type        | Notes                           |
|-------------|-------------|---------------------------------|
| outageId    | UUID (PK)   | Consensus event ID              |
| payload     | JSONB       | Serialized recordOutage args    |
| retryCount  | INTEGER     | Default 0                       |
| createdAt   | TIMESTAMPTZ | When write failed               |

---

## Behavioral Rules

### DO:
- Escalate to blockchain only on confirmed consensus (≥60% nodes)
- Queue reports locally on agent if API is unreachable
- Filter false positives (silent nodes, single-device failures)
- Buffer pending chain writes to DB if oracle wallet is out of gas
- Use exponential backoff for all retry logic
- Verify HMAC signatures on all incoming reports

### DO NOT:
- Write unverified or inconclusive events to the blockchain
- Allow the same outageId to be recorded twice on-chain
- Trust a single node's report under any circumstance
- Skip NTP timestamp validation on agent reports
- Process reports from nodes silent for >5 minutes

---

## Consensus Rules

- **CONFIRMED**: ≥60% of active nodes in region report DOWN/TIMEOUT
- **INCONCLUSIVE**: Window closes with <60% consensus → log only
- **RESOLVED**: Target returns UP for consecutive checks
- **REGION_BLACKOUT**: ALL nodes in region silent → special event type

---

## Architecture Invariants

1. Agent never trusts its own clock — always NTP-synced
2. API validates schema BEFORE any storage operation
3. Consensus engine reads ONLY from Redis sorted sets
4. Blockchain writes are async and non-blocking for the dashboard
5. Dashboard reads from Neon as fallback when RPC is slow
6. Every layer logs to findings.md when discovering new constraints
