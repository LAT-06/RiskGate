# System Overview

## Purpose

RiskGate is a transaction risk assessment and fraud investigation
platform integrated with a minimal digital banking simulator.

The banking simulator generates authentication, device, beneficiary,
and transaction data. RiskGate is the primary product.

## Actors

- Customer
- Fraud Analyst
- Security Administrator

## Main Components

- Customer banking web
- Analyst dashboard
- Banking API
- Transaction service
- RiskGate
- Ledger
- Investigation service
- Agent and RAG assistant
- Audit and monitoring pipeline

## High-Level Flow

Customer submits transaction
→ Transaction service validates request
→ RiskGate evaluates transaction
→ ALLOW, CHALLENGE, HOLD, or DENY
→ Ledger or investigation workflow

## AWS Architecture

- CloudFront and WAF
- API Gateway
- Cognito
- Lambda
- DynamoDB
- Aurora PostgreSQL
- EventBridge
- SQS
- S3
- CloudWatch
- Bedrock

## Core Principles

- Risk decisions are deterministic.
- Agent output is advisory.
- Ledger changes are atomic and idempotent.
- Structured data is queried from databases.
- RAG is used only for unstructured knowledge.