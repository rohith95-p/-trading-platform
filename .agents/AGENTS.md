# Antigravity Agent Execution Hierarchy

This file orchestrates the workflow for the Antigravity agent when working in this repository. 
Do not blindly modify code or test strategies. Enforce the following hierarchy.

## Execution Hierarchy

```mermaid
graph TD
    AG[AGENTS.md Orchestrator] --> RG[01-repo-guardian]
    RG --> ENG[ENGINEERING SKILLS]
    RG --> RES[RESEARCH SKILLS]
    
    subgraph Engineering
    ENG --> CA[02-code-auditor]
    ENG --> TE[03-test-engineer]
    ENG --> DV[06-data-validator]
    ENG --> PO[09-performance-optimizer]
    end
    
    subgraph Research
    RES --> MR[12-market-researcher]
    RES --> SD[13-strategy-discovery]
    SD --> BA[11-backtest-auditor]
    BA --> OOS[16-walkforward-validator]
    BA --> ST[17-stress-tester]
    BA --> PA[18-portfolio-auditor]
    OOS --> AF[20-account-feasibility]
    ST --> AF
    PA --> AF
    AF --> PV[04-research-scientist / Paper Validation]
    end
```

## Protocol
1. **Research skill** discovers or tests a concept.
2. **Experiment skill** isolates and logs the test.
3. **Audit skill** rigorously verifies the test data.
4. **Validation skill** approves or rejects it.
5. **Only then** can production modifications be considered.
