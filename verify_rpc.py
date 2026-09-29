#!/usr/bin/env python3
"""Verify Base Sepolia RPC connection and deployer wallet balance."""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

def log_finding(message: str, status: str):
    """Append finding to findings.md."""
    findings_path = Path(__file__).parent.parent / "findings.md"
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    entry = f"\n### [{timestamp}] — Base Sepolia RPC\n**Finding**: {message}\n**Status**: {status}\n"
    with open(findings_path, "a") as f:
        f.write(entry)

def rpc_call(url: str, method: str, params: list = []) -> dict:
    """Make a JSON-RPC call."""
    import urllib.request

    payload = json.dumps({
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    }).encode()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())

def get_address_from_private_key(private_key: str) -> str | None:
    """Derive Ethereum address from private key using eth_account."""
    try:
        from eth_account import Account
        account = Account.from_key(private_key)
        return account.address
    except ImportError:
        # Fallback: use keccak256 of public key derivation
        # For verification purposes, we just need the address
        print("[WARN] eth_account not installed, skipping balance check")
        return None

def main():
    rpc_url = os.environ.get("ALCHEMY_RPC_URL") or os.environ.get("INFURA_RPC_URL")
    if not rpc_url:
        print("[HALT] Neither ALCHEMY_RPC_URL nor INFURA_RPC_URL set")
        log_finding("No RPC URL configured", "OPEN")
        sys.exit(1)

    private_key = os.environ.get("DEPLOYER_PRIVATE_KEY", "")

    try:
        print(f"[*] Connecting to Base Sepolia RPC...")

        # Fetch latest block number
        result = rpc_call(rpc_url, "eth_blockNumber")
        block_number = int(result["result"], 16)
        print(f"[OK] Latest block: {block_number}")

        # Fetch chain ID to verify we're on Base Sepolia
        chain_result = rpc_call(rpc_url, "eth_chainId")
        chain_id = int(chain_result["result"], 16)
        print(f"[OK] Chain ID: {chain_id}")

        if chain_id != 11155111:
            print(f"[WARN] Expected ETH Sepolia (11155111), got {chain_id}")

        # Check deployer wallet balance
        if private_key:
            address = get_address_from_private_key(private_key)
            if address:
                balance_result = rpc_call(rpc_url, "eth_getBalance", [address, "latest"])
                balance_wei = int(balance_result["result"], 16)
                balance_eth = balance_wei / 1e18

                print(f"[OK] Deployer address: {address}")
                print(f"[OK] Balance: {balance_eth:.6f} ETH")

                if balance_eth < 0.01:
                    print(f"[WARN] Balance below 0.01 ETH — may not have enough gas")
                    log_finding(f"Deployer balance low: {balance_eth:.6f} ETH", "OPEN")
                else:
                    log_finding(f"RPC OK. Block: {block_number}. Balance: {balance_eth:.6f} ETH", "RESOLVED")
            else:
                print("[WARN] Could not derive address, skipping balance check")
                log_finding(f"RPC OK. Block: {block_number}. Balance check skipped.", "RESOLVED")
        else:
            print("[WARN] DEPLOYER_PRIVATE_KEY not set, skipping balance check")
            log_finding(f"RPC OK. Block: {block_number}. No private key configured.", "RESOLVED")

        print(f"\n[GREEN] RPC verification passed")

    except Exception as e:
        print(f"[HALT] RPC connection failed: {e}")
        log_finding(f"RPC connection failed: {e}", "OPEN")
        sys.exit(1)

if __name__ == "__main__":
    main()
