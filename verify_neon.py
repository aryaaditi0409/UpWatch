#!/usr/bin/env python3
"""Verify Neon Postgres connection via DATABASE_URL."""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

def log_finding(message: str, status: str):
    """Append finding to findings.md."""
    findings_path = Path(__file__).parent.parent / "findings.md"
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    entry = f"\n### [{timestamp}] — Neon Postgres\n**Finding**: {message}\n**Status**: {status}\n"
    with open(findings_path, "a") as f:
        f.write(entry)

def main():
    try:
        import psycopg2
    except ImportError:
        print("[HALT] psycopg2 not installed. Run: pip install psycopg2-binary")
        log_finding("psycopg2 not installed", "OPEN")
        sys.exit(1)

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("[HALT] DATABASE_URL not set in environment")
        log_finding("DATABASE_URL not set", "OPEN")
        sys.exit(1)

    try:
        print(f"[*] Connecting to Neon...")
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()

        cur.execute("SELECT NOW();")
        row = cur.fetchone()
        if row is None:
            raise Exception("SELECT NOW() returned no rows")
        server_time = row[0]

        print(f"[OK] Neon connected successfully")
        print(f"[OK] Server time: {server_time}")

        # Check if tables exist
        cur.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public';
        """)
        tables = [row[0] for row in cur.fetchall()]
        print(f"[OK] Existing tables: {tables if tables else 'none (fresh database)'}")

        cur.close()
        conn.close()

        log_finding(f"Neon connection OK. Server time: {server_time}. Tables: {tables}", "RESOLVED")
        print("\n[GREEN] Neon verification passed")

    except Exception as e:
        print(f"[HALT] Neon connection failed: {e}")
        log_finding(f"Neon connection failed: {e}", "OPEN")
        sys.exit(1)

if __name__ == "__main__":
    main()
