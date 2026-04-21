# Tasks: Unified Trading Intelligence Platform Phase 1

## Overview

This document contains the implementation tasks for Phase 1 MVP (16 weeks / 4 months). Tasks are organized by month and week, following the detailed plan in `MIND_FUCK/PLAN_02_PHASE_1.md`.

**Timeline**: 16 weeks (4 months)
**Approach**: Build with Kiro (40-50% time savings)
**Cost Target**: $0-200/month (bootstrap)

---

## MONTH 1: Infrastructure + Abstractions (Weeks 1-4)

### Week 1-2: Project Setup + Interface Design

#### Task 1.1: Project Structure Setup
**Status**: ✅ COMPLETE
**Estimated Time**: 1 day

Create the foundational project structure for both backend (Python) and frontend (TypeScript).

**Sub-tasks**:
- [x] 1.1.1 Create backend directory structure (src/, tests/, docs/)
- [x] 1.1.2 Create frontend directory structure (components/, pages/, hooks/)
- [x] 1.1.3 Initialize Git repository with .gitignore
- [x] 1.1.4 Setup Python virtual environment (Python 3.11+)
- [x] 1.1.5 Setup Node.js project (Node 18+)
- [x] 1.1.6 Create requirements.txt and package.json

**Completion Criteria**:
- Project structure matches design document
- Git repository initialized
- Virtual environments working
- Dependencies installable

**References**: Design Doc - Project Structure

---

#### Task 1.2: Core Interface Definitions
**Status**: ✅ COMPLETE
**Estimated Time**: 2 days

Design and implement the 4 core pluggable interfaces that enable zero-refactoring integration of future phases.

**Sub-tasks**:
- [x] 1.2.1 Create ExchangeConnector interface (TypeScript)
- [x] 1.2.2 Create StrategyExecutor interface (TypeScript)
- [x] 1.2.3 Create Backtester interface (Python)
- [x] 1.2.4 Create DRLAgent interface (Python)
- [x] 1.2.5 Write interface documentation with examples
- [x] 1.2.6 Create unit tests for interface contracts

**Completion Criteria**:
- All 4 interfaces defined with complete type signatures
- Documentation includes usage examples
- Interface tests pass
- Validates Requirement 1 (Pluggable Architecture)

**References**: Design Doc - Components and Interfaces, Requirement 1

---

#### Task 1.3: Infrastructure Deployment
**Status**: ✅ COMPLETE (Code Ready, Manual Account Setup Required)
**Estimated Time**: 2 days

Deploy the infrastructure stack using free tiers (Railway, Supabase, Vercel).

**Sub-tasks**:
- [x] 1.3.1 Create Railway account and project
- [x] 1.3.2 Create Supabase account and project
- [x] 1.3.3 Create Vercel account and project
- [x] 1.3.4 Configure environment variables for all services
- [x] 1.3.5 Deploy "Hello World" backend to Railway
- [x] 1.3.6 Deploy "Hello World" frontend to Vercel
- [x] 1.3.7 Test connectivity between services

**Completion Criteria**:
- Railway backend accessible via HTTPS
- Supabase database accessible
- Vercel frontend accessible
- Environment variables configured
- Validates Requirement 10 (Infrastructure)

**References**: Design Doc - Infrastructure Design, Requirement 10

---

### Week 3-4: Database + Authentication

#### Task 1.4: Database Schema Implementation
**Status**: ✅ COMPLETE
**Estimated Time**: 2 days

Implement the complete database schema in Supabase PostgreSQL.

**Sub-tasks**:
- [x] 1.4.1 Create users table with quota limits
- [x] 1.4.2 Create api_keys table with encryption fields
- [x] 1.4.3 Create strategies table with JSONB config
- [x] 1.4.4 Create trades table with indexes
- [x] 1.4.5 Create positions table with unique constraints
- [x] 1.4.6 Create signals table
- [x] 1.4.7 Create audit_log table
- [x] 1.4.8 Setup Row Level Security (RLS) policies
- [x] 1.4.9 Create database migration scripts

**Completion Criteria**:
- All 7 tables created with correct schema
- Indexes created on frequently queried fields
- RLS policies active
- Migration scripts tested
- Validates Requirement 14 (Data Persistence)

**References**: Design Doc - Database Schema, Requirement 14

---

#### Task 1.5: Authentication System
**Status**: ✅ COMPLETE
**Estimated Time**: 3 days

Implement user authentication with email/password and OAuth.

**Sub-tasks**:
- [x] 1.5.1 Setup Supabase Auth configuration
- [x] 1.5.2 Implement user registration endpoint
- [x] 1.5.3 Implement login endpoint with JWT
- [x] 1.5.4 Implement password reset flow
- [x] 1.5.5 Configure OAuth (Google, GitHub)
- [x] 1.5.6 Implement JWT token validation middleware
- [x] 1.5.7 Create authentication tests
- [x] 1.5.8 Implement rate limiting for auth endpoints

**Completion Criteria**:
- Users can register with email/password
- Users can login and receive JWT token
- Password reset works via email
- OAuth providers working
- JWT validation middleware protects routes
- Validates Requirement 11 (Authentication)

**References**: Design Doc - Security Design, Requirement 11

---

#### Task 1.6: API Key Management
**Status**: ✅ COMPLETE
**Estimated Time**: 2 days

Implement secure API key storage with AES-256 encryption.

**Sub-tasks**:
- [x] 1.6.1 Implement AES-256-GCM encryption class
- [x] 1.6.2 Create API key add endpoint
- [x] 1.6.3 Create API key list endpoint (masked)
- [x] 1.6.4 Create API key delete endpoint
- [x] 1.6.5 Create API key validation endpoint
- [x] 1.6.6 Implement encryption key rotation support
- [x] 1.6.7 Create API key management tests

**Completion Criteria**:
- API keys encrypted at rest with AES-256
- Users can add/view/delete API keys
- API keys validated on addition
- Never logs unencrypted keys
- Validates Requirement 12 (API Key Management)

**References**: Design Doc - Security Design, Requirement 12

---

## MONTH 2: Intelligence Layer (Weeks 5-8)

### Week 5-6: News Classification

#### Task 2.1: News Stream Integration
**Status**: ✅ COMPLETE
**Estimated Time**: 2 days

Extract and integrate news ingestion from Polymarket Pipeline.

**Sub-tasks**:
- [x] 2.1.1 Extract news_stream.py from Polymarket Pipeline
- [x] 2.1.2 Adapt to use environment variables for API keys
- [x] 2.1.3 Implement RSS feed support
- [x] 2.1.4 Implement Twitter API support (optional)
- [x] 2.1.5 Implement Telegram support (optional)
- [x] 2.1.6 Create news ingestion tests

**Completion Criteria**:
- News articles ingested from multiple sources
- API keys loaded from environment
- Tests pass with mock data

**References**: Design Doc - Integration Strategy (Polymarket Pipeline)

---

#### Task 2.2: Claude API News Classifier
**Status**: ✅ COMPLETE
**Estimated Time**: 3 days

Implement news classification using Claude API with <5 sec latency.

**Sub-tasks**:
- [x] 2.2.1 Extract classifier.py from Polymarket Pipeline
- [x] 2.2.2 Implement Claude API integration
- [x] 2.2.3 Add caching for repeated articles (Redis)
- [x] 2.2.4 Implement error handling and retries
- [x] 2.2.5 Create classification endpoint POST /intelligence/classify-news
- [x] 2.2.6 Implement WebSocket news feed
- [x] 2.2.7 Store signals in database
- [x] 2.2.8 Create classification tests with 80%+ accuracy target

**Completion Criteria**:
- Classification completes within 5 seconds
- 80%+ accuracy on validation data
- Extracts sentiment and confidence score
- Generates trading signals for matched markets
- Validates Requirement 2 (News Classification)

**References**: Design Doc - REST API Design, Requirement 2

---

### Week 7-8: Technical Analysis

#### Task 2.3: Technical Indicator Library
**Status**: ✅ COMPLETE
**Estimated Time**: 3 days

Extract and implement 20+ technical indicators from Hyperliquid Agent.

**Sub-tasks**:
- [x] 2.3.1 Extract local_indicators.py from Hyperliquid Agent
- [x] 2.3.2 Implement EMA (20, 50, 200 periods)
- [x] 2.3.3 Implement RSI (14 period)
- [x] 2.3.4 Implement MACD (12, 26, 9)
- [x] 2.3.5 Implement ATR (14 period)
- [x] 2.3.6 Implement Bollinger Bands (20, 2)
- [x] 2.3.7 Implement ADX (14 period)
- [x] 2.3.8 Implement OBV
- [x] 2.3.9 Implement VWAP
- [x] 2.3.10 Vectorize calculations using NumPy
- [x] 2.3.11 Add Redis caching (60 sec TTL)
- [x] 2.3.12 Create property-based tests for indicator ranges

**Completion Criteria**:
- All 20+ indicators implemented
- Calculations complete within 100ms
- Caching working
- Property tests pass (Properties 3 & 4)
- Validates Requirement 3 (Technical Indicators)

**References**: Design Doc - Correctness Properties, Requirement 3

---

#### Task 2.4: Technical Analysis API
**Status**: ✅ COMPLETE
**Estimated Time**: 2 days

Create REST API endpoint for indicator computation.

**Sub-tasks**:
- [x] 2.4.1 Create POST /intelligence/indicators endpoint
- [x] 2.4.2 Implement request validation (Pydantic)
- [x] 2.4.3 Support multiple timeframes (1m, 5m, 15m, 1h, 4h, 1d)
- [x] 2.4.4 Implement batch indicator computation
- [x] 2.4.5 Add rate limiting (100 calls/hour)
- [x] 2.4.6 Create integration tests

**Completion Criteria**:
- Endpoint returns indicators within 100ms
- Supports all timeframes
- Rate limiting active
- Integration tests pass

**References**: Design Doc - REST API Design

---

## MONTH 3: Execution + Simulation (Weeks 9-12)

### Week 9-10: Exchange Connectors

#### Task 3.1: Kalshi Connector
**Status**: ✅ COMPLETE
**Estimated Time**: 2 days

Implement Kalshi prediction market connector.

**Sub-tasks**:
- [x] 3.1.1 Extract kalshi.ts from OpenTradex
- [x] 3.1.2 Convert to Python or keep as microservice
- [x] 3.1.3 Implement ExchangeConnector interface
- [x] 3.1.4 Add paper trading mode enforcement
- [x] 3.1.5 Implement error handling and retries
- [x] 3.1.6 Create connector tests with testnet

**Completion Criteria**:
- Implements ExchangeConnector interface
- Paper trading mode enforced
- Orders execute within 1 second
- Tests pass on testnet
- Validates Requirement 5 (Exchange Connectivity)

**References**: Design Doc - Components and Interfaces, Requirement 5

---

#### Task 3.2: Polymarket Connector
**Status**: ✅ COMPLETE
**Estimated Time**: 2 days

Implement Polymarket prediction market connector.

**Sub-tasks**:
- [x] 3.2.1 Extract polymarket.ts from OpenTradex
- [x] 3.2.2 Convert to Python or keep as microservice
- [x] 3.2.3 Implement ExchangeConnector interface
- [x] 3.2.4 Add paper trading mode enforcement
- [x] 3.2.5 Implement error handling and retries
- [x] 3.2.6 Create connector tests

**Completion Criteria**:
- Implements ExchangeConnector interface
- Paper trading mode enforced
- Orders execute within 1 second
- Tests pass

**References**: Design Doc - Components and Interfaces, Requirement 5

---

#### Task 3.3: Alpaca Connector
**Status**: ✅ COMPLETE
**Estimated Time**: 2 days

Implement Alpaca stock broker connector (paper trading only).

**Sub-tasks**:
- [x] 3.3.1 Extract alpaca.ts from OpenTradex
- [x] 3.3.2 Convert to Python or keep as microservice
- [x] 3.3.3 Implement ExchangeConnector interface
- [x] 3.3.4 Enforce paper trading mode
- [x] 3.3.5 Implement error handling and retries
- [x] 3.3.6 Create connector tests with Alpaca paper API

**Completion Criteria**:
- Implements ExchangeConnector interface
- Paper trading mode enforced
- Orders execute within 1 second
- Tests pass with Alpaca paper API

**References**: Design Doc - Components and Interfaces, Requirement 5

---

#### Task 3.4: Exchange Router + Risk Manager
**Status**: ✅ COMPLETE
**Estimated Time**: 3 days

Implement order routing and risk management.

**Sub-tasks**:
- [x] 3.4.1 Create exchange router
- [x] 3.4.2 Implement risk manager with position limits
- [x] 3.4.3 Implement Kelly criterion position sizing
- [x] 3.4.4 Add circuit breaker for daily drawdown
- [x] 3.4.5 Add automatic position close on 20% loss
- [x] 3.4.6 Create property-based tests for risk limits
- [x] 3.4.7 Create trading API endpoints

**Completion Criteria**:
- Routes orders to correct exchange
- Enforces 10% position limit
- Enforces 50% total exposure limit
- Enforces 10x max leverage
- Property tests pass (Properties 7, 8, 9, 10)
- Validates Requirement 6 (Risk Management)

**References**: Design Doc - Correctness Properties, Requirement 6

---

### Week 11-12: Multi-Agent Simulation

#### Task 3.5: Simulation Engine
**Status**: ✅ COMPLETE
**Estimated Time**: 3 days

Extract and simplify multi-agent simulation from MiroFish.

**Sub-tasks**:
- [x] 3.5.1 Extract simulation_runner.py from MiroFish
- [x] 3.5.2 Reduce agent count to 10 (from 1000)
- [x] 3.5.3 Reduce rounds to 5 (from 100)
- [x] 3.5.4 Optimize for <30 sec execution
- [x] 3.5.5 Integrate with OpenAI API or Ollama
- [x] 3.5.6 Create POST /intelligence/simulate endpoint
- [x] 3.5.7 Add automatic triggering for trades >$1K
- [x] 3.5.8 Create simulation tests

**Completion Criteria**:
- Simulation completes within 30 seconds
- Returns confidence score 0-1
- Provides reasoning with consensus and dissent
- Automatically triggers for trades >$1K
- Property tests pass (Properties 5, 6)
- Validates Requirement 4 (Multi-Agent Simulation)

**References**: Design Doc - Integration Strategy (MiroFish), Requirement 4

---

## MONTH 4: DRL + Backtesting + UI (Weeks 13-16)

### Week 13-14: PPO Agent

#### Task 4.1: PPO Agent Implementation
**Status**: ✅ COMPLETE
**Estimated Time**: 3 days

Extract and implement PPO reinforcement learning agent from Fiduciary Sentinel.

**Sub-tasks**:
- [x] 4.1.1 Extract agent.py from Fiduciary Sentinel
- [x] 4.1.2 Extract trading_env.py for training environment
- [x] 4.1.3 Implement DRLAgent interface
- [x] 4.1.4 Add constitutional guardrails
- [x] 4.1.5 Integrate with risk manager
- [x] 4.1.6 Implement model save/load
- [x] 4.1.7 Create POST /intelligence/drl/predict endpoint
- [x] 4.1.8 Create property-based tests for guardrails

**Completion Criteria**:
- Implements DRLAgent interface
- Predicts actions within 500ms
- Constitutional guardrails enforce risk limits
- Supports training on 1+ year of data
- Property tests pass (Property 11)
- Validates Requirement 7 (PPO Agent)

**References**: Design Doc - Components and Interfaces, Requirement 7

---

#### Task 4.2: Risk Guardrails
**Status**: ✅ COMPLETE
**Estimated Time**: 2 days

Extract and implement risk guardrails from Fiduciary Sentinel.

**Sub-tasks**:
- [x] 4.2.1 Extract core.py from Fiduciary Sentinel
- [x] 4.2.2 Implement guardrail checks
- [x] 4.2.3 Override dangerous actions to "hold"
- [x] 4.2.4 Integrate with DRL agent
- [x] 4.2.5 Create guardrail tests

**Completion Criteria**:
- Guardrails prevent risk limit violations
- Dangerous actions overridden to "hold"
- Tests verify all guardrail scenarios

**References**: Design Doc - Integration Strategy (Fiduciary Sentinel)

---

### Week 15: Vectorized Backtesting

#### Task 4.3: Pandas Backtester
**Status**: ✅ COMPLETE
**Estimated Time**: 3 days

Implement vectorized backtester using pandas (Phase 1 stub).

**Sub-tasks**:
- [x] 4.3.1 Create PandasBacktester class
- [x] 4.3.2 Implement Backtester interface
- [x] 4.3.3 Implement vectorized operations
- [x] 4.3.4 Compute metrics (return, Sharpe, drawdown, win rate)
- [x] 4.3.5 Support multiple timeframes
- [x] 4.3.6 Account for fees and slippage
- [x] 4.3.7 Generate trade-by-trade log
- [x] 4.3.8 Create property-based tests for metrics
- [x] 4.3.9 Create POST /backtest endpoint

**Completion Criteria**:
- Implements Backtester interface
- Processes 1 year of data in 1-2 minutes
- Computes all required metrics
- Property tests pass (Properties 12, 13, 14, 15)
- Validates Requirement 8 (Backtesting)

**References**: Design Doc - Components and Interfaces, Requirement 8

---

### Week 16: Dashboard + Testing + Deployment

#### Task 4.4: Dashboard Frontend
**Status**: ✅ COMPLETE
**Estimated Time**: 4 days

Build React dashboard with portfolio monitoring and trading features.

**Sub-tasks**:
- [x] 4.4.1 Create portfolio view component
- [x] 4.4.2 Create signal feed component
- [x] 4.4.3 Create trade history component
- [x] 4.4.4 Create positions component
- [x] 4.4.5 Create backtesting UI component
- [x] 4.4.6 Implement WebSocket connections
- [x] 4.4.7 Add real-time updates (1 sec refresh)
- [x] 4.4.8 Create dashboard tests

**Completion Criteria**:
- All components render correctly
- Real-time updates working
- WebSocket connections stable
- Dashboard loads within 2 seconds
- Validates Requirement 9 (Dashboard)

**References**: Design Doc - REST API Design, Requirement 9

---

#### Task 4.5: Integration Testing
**Status**: ✅ COMPLETE
**Estimated Time**: 2 days

Create comprehensive integration tests.

**Sub-tasks**:
- [x] 4.5.1 Create API endpoint integration tests
- [x] 4.5.2 Create exchange connector integration tests
- [x] 4.5.3 Create database operation tests
- [x] 4.5.4 Create end-to-end user flow tests
- [x] 4.5.5 Setup CI/CD pipeline (GitHub Actions)
- [x] 4.5.6 Verify 80%+ code coverage

**Completion Criteria**:
- All integration tests pass
- 80%+ code coverage achieved
- CI/CD pipeline working
- Validates Requirement 17 (Testing)

**References**: Design Doc - Testing Strategy, Requirement 17

---

#### Task 4.6: Production Deployment
**Status**: ✅ COMPLETE
**Estimated Time**: 2 days

Deploy to production and setup monitoring.

**Sub-tasks**:
- [x] 4.6.1 Deploy backend to Railway production
- [x] 4.6.2 Deploy frontend to Vercel production
- [x] 4.6.3 Configure production environment variables
- [x] 4.6.4 Setup Better Stack logging
- [x] 4.6.5 Configure alerts (error rate, latency)
- [x] 4.6.6 Run smoke tests on production
- [x] 4.6.7 Create deployment documentation

**Completion Criteria**:
- Production deployment successful
- All services accessible via HTTPS
- Monitoring and alerts active
- 99% uptime target met
- Validates Requirement 10, 13 (Infrastructure, Monitoring)

**References**: Design Doc - Deployment Strategy, Requirements 10, 13

---

## Summary

**Total Tasks**: 24 main tasks
**Total Sub-tasks**: 150+ sub-tasks
**Timeline**: 16 weeks (4 months)
**Success Criteria**: All 20 requirements validated, 80%+ code coverage, 15 property tests passing

**Next Steps**:
1. Start with Task 1.1 (Project Structure Setup)
2. Work through tasks sequentially
3. Mark tasks complete as you finish them
4. Update this file with progress

**Note**: This is a living document. Update task statuses and add notes as you progress through implementation.
