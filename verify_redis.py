#!/usr/bin/env python3
"""Verify Redis connection and pub/sub via REDIS_URL."""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

def log_finding(message: str, status: str):
    """Append finding to findings.md."""
    findings_path = Path(__file__).parent.parent / "findings.md"
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    entry = f"\n### [{timestamp}] — Redis\n**Finding**: {message}\n**Status**: {status}\n"
    with open(findings_path, "a") as f:
        f.write(entry)

def main():
    try:
        import redis
    except ImportError:
        print("[HALT] redis not installed. Run: pip install redis")
        log_finding("redis-py not installed", "OPEN")
        sys.exit(1)

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")

    try:
        print(f"[*] Connecting to Redis at {redis_url.split('@')[-1] if '@' in redis_url else redis_url}...")
        r = redis.from_url(redis_url, decode_responses=True)

        # Test PING
        pong = r.ping()
        if pong:
            print(f"[OK] Redis PING -> PONG")
        else:
            raise Exception("PING returned False")

        # Test pub/sub
        print(f"[*] Testing pub/sub on channel 'outages:live'...")
        test_channel = "outages:live"
        test_message = '{"test": true, "timestamp": "' + datetime.utcnow().isoformat() + '"}'

        pubsub = r.pubsub()
        pubsub.subscribe(test_channel)

        # Publish test message
        r.publish(test_channel, test_message)

        # Wait for message with timeout
        received = False
        start = time.time()
        while time.time() - start < 2:
            msg = pubsub.get_message(timeout=0.5)
            if msg and msg["type"] == "message":
                print(f"[OK] Pub/sub received: {msg['data'][:80]}...")
                received = True
                break

        pubsub.unsubscribe()
        pubsub.close()

        if not received:
            raise Exception("Pub/sub message not received within 2s")

        print(f"[OK] Redis pub/sub verified on '{test_channel}'")

        r.close()
        log_finding("Redis PING + pub/sub OK", "RESOLVED")
        print("\n[GREEN] Redis verification passed")

    except Exception as e:
        print(f"[HALT] Redis connection failed: {e}")
        log_finding(f"Redis connection failed: {e}", "OPEN")
        sys.exit(1)

if __name__ == "__main__":
    main()
