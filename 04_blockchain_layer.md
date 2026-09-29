# Architecture SOP — Blockchain Layer

> Layer 1: Oracle flow, gas handling, retry logic

---

## Overview

The blockchain layer handles writing confirmed outages to the Base Sepolia blockchain via the OutageLedger.sol contract, with retry logic for failed transactions.

## Oracle Flow

```
Consensus Worker (CONFIRMED)
  → Enqueue BullMQ job "blockchain:write"
  → Oracle worker picks up job
  → Sign tx with DEPLOYER_PRIVATE_KEY
  → Call OutageLedger.recordOutage()
  → On success: update Neon outages table with txHash
  → On failure: write to pending_chain_writes table
```

## Contract Interaction

### OutageLedger.recordOutage()

```solidity
function recordOutage(
    bytes32 outageId,
    string memory targetUrl,
    string memory region,
    uint256 startTimestamp,
    uint8 consensusScore,
    uint16 affectedNodes
) external onlyOracle {
    if (outages[outageId].startTimestamp != 0) {
        revert AlreadyRecorded();
    }
    // ... store outage
    emit OutageRecorded(outageId, targetUrl, region, startTimestamp, consensusScore, affectedNodes);
}
```

### SLAEscrow.triggerPenalty()

```solidity
function triggerPenalty(
    bytes32 outageId,
    address clientAddress
) external onlyOracle {
    // ... calculate penalty based on outage duration
    // ... transfer from escrow to protocol treasury
    emit PenaltyTriggered(outageId, clientAddress, penaltyAmount);
}
```

## Oracle Implementation (`oracle.ts`)

```typescript
import { createWalletClient, http, parseAbi } from "viem";
import { baseSepolia } from "viem/chains";

const walletClient = createWalletClient({
  chain: baseSepolia,
  transport: http(process.env.ALCHEMY_RPC_URL),
  account: process.env.DEPLOYER_PRIVATE_KEY as `0x${string}`,
});

async function recordOutage(consensus: ConsensusEvent) {
  try {
    const txHash = await walletClient.writeContract({
      address: OUTAGE_LEDGER_ADDRESS,
      abi: OUTAGE_LEDGER_ABI,
      functionName: "recordOutage",
      args: [
        consensus.outageId,
        consensus.targetUrl,
        consensus.region,
        BigInt(Math.floor(new Date(consensus.startTimestamp).getTime() / 1000)),
        Math.round(consensus.consensusScore * 100),
        consensus.affectedNodeCount,
      ],
    });

    // Update Neon with txHash
    await updateOutageTxHash(consensus.outageId, txHash);

  } catch (error) {
    // Gas failure or RPC error
    await storePendingWrite(consensus, error);
  }
}
```

## Gas Failure Handling

### Detection
- `InsufficientFundsError` from viem
- `Gas estimation failed` from RPC
- Transaction reverted

### Recovery
```sql
INSERT INTO pending_chain_writes (outageId, payload, retryCount, createdAt)
VALUES ($1, $2, 0, NOW())
ON CONFLICT (outageId) DO UPDATE SET retryCount = pending_chain_writes.retryCount + 1;
```

## Retry Worker (`retryWorker.ts`)

- Polls `pending_chain_writes` table every 60 seconds
- Max retries: 10 (exponential backoff: 60s, 120s, 240s...)
- On success: delete from `pending_chain_writes`
- On max retries: log to findings.md, alert operator

```typescript
setInterval(async () => {
  const pending = await db.query(
    "SELECT * FROM pending_chain_writes WHERE retryCount < 10 ORDER BY createdAt ASC LIMIT 5"
  );

  for (const write of pending.rows) {
    await recordOutage(JSON.parse(write.payload));
  }
}, 60_000);
```

## Duplicate Guard

- Contract checks `outages[outageId].startTimestamp != 0`
- Reverts with `AlreadyRecorded()` custom error
- Oracle catches revert, logs, skips to next job

## Events

### OutageRecorded
```solidity
event OutageRecorded(
    bytes32 indexed outageId,
    string targetUrl,
    string region,
    uint256 startTimestamp,
    uint8 consensusScore,
    uint16 affectedNodes
);
```

### PenaltyTriggered
```solidity
event PenaltyTriggered(
    bytes32 indexed outageId,
    address indexed clientAddress,
    uint256 penaltyAmount
);
```
