-- Upwatch Database Schema
-- Run on first container start

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Nodes table
CREATE TABLE IF NOT EXISTS nodes (
    nodeId UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    region VARCHAR(64) NOT NULL,
    lastSeenAt TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    isActive BOOLEAN NOT NULL DEFAULT true
);

-- Reports table
CREATE TABLE IF NOT EXISTS reports (
    id BIGSERIAL PRIMARY KEY,
    nodeId UUID NOT NULL REFERENCES nodes(nodeId),
    targetUrl TEXT NOT NULL,
    region VARCHAR(64) NOT NULL,
    status VARCHAR(16) NOT NULL CHECK (status IN ('UP', 'DOWN', 'TIMEOUT', 'DEGRADED')),
    latencyMs INTEGER,
    httpStatusCode INTEGER,
    timestamp TIMESTAMPTZ NOT NULL,
    createdAt TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_reports_nodeId ON reports(nodeId);
CREATE INDEX idx_reports_targetUrl ON reports(targetUrl);
CREATE INDEX idx_reports_timestamp ON reports(timestamp);

-- Outages table
CREATE TABLE IF NOT EXISTS outages (
    outageId UUID PRIMARY KEY,
    targetUrl TEXT NOT NULL,
    region VARCHAR(64) NOT NULL,
    startTimestamp TIMESTAMPTZ NOT NULL,
    consensusScore DECIMAL(3,2) NOT NULL CHECK (consensusScore >= 0 AND consensusScore <= 1),
    affectedNodeCount INTEGER NOT NULL,
    onChainTxHash TEXT,
    status VARCHAR(16) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('CONFIRMED', 'RESOLVED', 'PENDING')),
    createdAt TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_outages_targetUrl ON outages(targetUrl);
CREATE INDEX idx_outages_region ON outages(region);
CREATE INDEX idx_outages_status ON outages(status);

-- SLA Contracts table
CREATE TABLE IF NOT EXISTS sla_contracts (
    id BIGSERIAL PRIMARY KEY,
    clientAddress TEXT NOT NULL,
    targetUrl TEXT NOT NULL,
    escrowAmount BIGINT NOT NULL,
    penaltyPerHour BIGINT NOT NULL,
    createdAt TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sla_contracts_clientAddress ON sla_contracts(clientAddress);

-- Pending Chain Writes table
CREATE TABLE IF NOT EXISTS pending_chain_writes (
    outageId UUID PRIMARY KEY,
    payload JSONB NOT NULL,
    retryCount INTEGER NOT NULL DEFAULT 0,
    createdAt TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
