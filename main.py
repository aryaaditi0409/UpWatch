"""Orchestrator: pinger -> signer -> POST -> queue fallback."""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

from core.pinger import ping_all
from core.signer import ensure_node_identity, sign_payload
from core import queue
from core.config import TargetConfig

# Load .env from project root
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")
load_dotenv(Path(__file__).parent / ".env")


# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def format_status(status: str) -> str:
    """Format status with color and icon."""
    if status == "UP":
        return f"{GREEN}UP{RESET}"
    elif status == "DOWN":
        return f"{RED}DOWN{RESET}"
    elif status == "TIMEOUT":
        return f"{YELLOW}TIMEOUT{RESET}"
    elif status == "DEGRADED":
        return f"{YELLOW}DEGRADED{RESET}"
    return status


def timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def get_ntp_time() -> str:
    """Get NTP-synced timestamp, fallback to system time."""
    try:
        import ntplib
        client = ntplib.NTPClient()
        response = client.request("pool.ntp.org", version=3, timeout=3)
        ntp_time = datetime.fromtimestamp(response.tx_time, tz=timezone.utc)
        return ntp_time.isoformat()
    except Exception:
        return datetime.now(tz=timezone.utc).isoformat()


def send_report(report: dict, api_url: str) -> bool:
    """Send a report to the ingestion API. Returns True on success."""
    try:
        resp = httpx.post(
            f"{api_url}/report",
            json=report,
            timeout=5.0,
        )
        return resp.status_code == 202
    except Exception:
        return False


async def run():
    """Main agent loop."""
    region = os.environ.get("AGENT_REGION", "unknown")
    api_url = os.environ.get("AGENT_API_URL", "http://localhost:3001")
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    interval = int(os.environ.get("AGENT_INTERVAL_SECONDS", "15"))

    node_id, secret = ensure_node_identity()

    # Initialize target config
    config = TargetConfig(api_url, region, redis_url)

    # Try to fetch targets from API
    print(f"{CYAN}[*] Fetching targets from API...{RESET}")
    if await config.fetch_targets():
        print(f"{GREEN}[OK] Loaded {len(config.targets)} targets from API{RESET}")
    else:
        print(f"{YELLOW}[WARN] API unreachable — falling back to AGENT_TARGETS env var{RESET}")

    targets = config.get_targets()
    if not targets:
        print(f"{RED}[HALT] No targets configured (API unreachable and AGENT_TARGETS not set){RESET}")
        sys.exit(1)

    print(f"{BOLD}{CYAN}=== Upwatch Prover Agent ==={RESET}")
    print(f"Node ID: {node_id}")
    print(f"Region:  {region}")
    print(f"Targets: {', '.join(targets)}")
    print(f"API:     {api_url}")
    print(f"Interval: {interval}s")
    print(f"Queue:   {queue.count()} pending")
    print()

    # Start Redis subscription in background
    asyncio.create_task(config.subscribe_updates())

    while True:
        # Get current targets (may have been updated by Redis)
        targets = config.get_targets()
        if not targets:
            await asyncio.sleep(interval)
            continue

        results = await ping_all(targets)

        # Try to flush queued reports first
        if queue.count() > 0:
            flushed = queue.flush(lambda r: send_report(r, api_url))
            if flushed > 0:
                print(f"{CYAN}[{timestamp()}] Flushed {flushed} queued reports{RESET}")

        # Process new results
        for result in results:
            ts = get_ntp_time()
            sig = sign_payload(secret, node_id, ts, region, result.target_url, result.status)

            report = {
                "nodeId": node_id,
                "nodeSignature": sig,
                "timestamp": ts,
                "region": region,
                "targetUrl": result.target_url,
                "latencyMs": result.latency_ms,
                "status": result.status,
                "httpStatusCode": result.http_status_code,
            }

            latency_str = f"{result.latency_ms}ms" if result.latency_ms is not None else "N/A"
            status_fmt = format_status(result.status)
            icon = "OK" if result.status == "UP" else "ERR"

            if send_report(report, api_url):
                print(f"[{timestamp()}] {icon} {result.target_url} -- {latency_str} {status_fmt}")
            else:
                queue.enqueue(report)
                print(f"[{timestamp()}] {icon} {result.target_url} -- {latency_str} {status_fmt} {YELLOW}(queued locally){RESET}")

        await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(run())
