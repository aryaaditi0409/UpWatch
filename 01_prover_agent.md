# Architecture SOP — Prover Agent

> Layer 1: How the Python agent works

---

## Overview

The prover agent is a Python async application that continuously monitors target URLs and submits reports to the ingestion API.

## Components

### 1. Pinger (`core/pinger.py`)
- Uses `httpx.AsyncClient` for non-blocking HTTP requests
- Measures latency in milliseconds from request start to response
- Records `httpStatusCode` on success, `null` on timeout
- Status mapping:
  - `200-299` → `UP`
  - `300-499` → `DEGRADED`
  - `500+` → `DOWN`
  - Timeout exception → `TIMEOUT` (latencyMs = null)

### 2. Signer (`core/signer.py`)
- Loads node secret from `~/.prover/node.key`
- Auto-generates random secret on first run if missing
- Signs payload with HMAC-SHA256
- Signature covers: `nodeId + timestamp + region + targetUrl + status`

### 3. Queue (`core/queue.py`)
- SQLite-backed local queue at `~/.prover/queue.db`
- Schema: `(id INTEGER PRIMARY KEY, payload TEXT, created_at TEXT, attempts INTEGER DEFAULT 0)`
- Stores failed reports when API is unreachable
- Exponential backoff: 1s, 2s, 4s, 8s, 16s, max 60s
- Flushes queue on successful API connection

### 4. Orchestrator (`main.py`)
- Reads config from `.env`:
  - `AGENT_TARGETS` — comma-separated URLs
  - `AGENT_INTERVAL_SECONDS` — ping interval (default 15)
  - `AGENT_REGION` — region identifier
  - `AGENT_API_URL` — ingestion API endpoint
- Flow: `pinger → signer → POST /report → queue on failure`

## Timestamp Handling

- Agent uses NTP-synced time via `ntplib`
- On NTP failure, falls back to system time with warning
- All timestamps are ISO8601 with timezone

## Error Handling

- API timeout: retry with backoff, store in local queue
- Network error: store in local queue, flush on reconnect
- Invalid response (4xx): log and discard (bad request, not retryable)
- Server error (5xx): retry with backoff

## CLI Output Format

```
[HH:MM:SS] ✅ target.com — 142ms UP
[HH:MM:SS] ❌ target.com — TIMEOUT queued locally
[HH:MM:SS] 📤 Flushed 3 queued reports to API
```
