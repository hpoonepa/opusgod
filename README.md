# OpusGod — Autonomous DeFi Intelligence Agent

> The only agent that earns its own living.

OpusGod is an autonomous DeFi intelligence agent that sells market analysis through the Olas marketplace, monitors Lido vaults with Telegram alerts, and funds all operations from Zyfai yield. Every HTTP request is cryptographically signed with ERC-8128, linked to its on-chain ERC-8004 identity, and deployable through Pearl with zero technical knowledge.

## Architecture

- **State Machine**: 6 states (STARTUP -> IDLE -> SERVING/MONITORING -> ANALYZING -> HIRING -> IDLE)
- **Chains**: Gnosis (Olas mech) + Base (Slice commerce)
- **LLM**: Bankr Gateway (routes to GPT-4o/Claude/Gemini)
- **Identity**: ERC-8128 signed requests + ERC-8004 on-chain identity

## Revenue Streams

| Stream | Source | Track |
|--------|--------|-------|
| Mech Fees | 5 DeFi analysis tools on Olas marketplace | Olas Monetize |
| Agent Hiring | Hires specialized agents for complex analysis | Olas Hire |
| Zyfai Yield | Self-funding from yield-bearing accounts | Zyfai |
| Slice Commerce | Dynamic-priced analysis reports | Slice Hooks |
| x402 Payments | Premium API access via ampersend | ampersend-sdk |

## 5 Mech Tools

1. **yield_optimizer** — Cross-protocol yield comparison
2. **risk_assessor** — Portfolio risk scoring (1-10)
3. **vault_monitor** — Real-time vault health + anomaly detection
4. **protocol_analyzer** — DeFi protocol safety analysis
5. **portfolio_rebalancer** — AI-driven rebalancing recommendations

## Quick Start

```bash
pip install -e ".[dev]"
cp .env.example .env
# Fill in your keys in .env
python -m src.agent.core
```

## Endpoints

| Port | Service | Endpoints |
|------|---------|-----------|
| 8716 | Pearl UI | GET /, /healthcheck, /funds-status |
| 8080 | Mech Server | POST /request, GET /tools, GET /health |

## Testing

```bash
python -m pytest tests/ -v
```

## Tracks (11)

Olas Monetize ($1K) | Olas Hire ($1K) | Olas Pearl ($1K) | ampersend-sdk ($500) | Bankr LLM ($5K) | Vault Monitor ($1.5K) | Zyfai Agent ($600) | Zyfai Infra ($400) | Slice Hooks ($700) | ERC-8128 ($750) | Synthesis Open ($28.1K)

## ERC-8128: First Python Implementation

OpusGod includes the first Python package for ERC-8128 HTTP Message Signatures. Every API request is cryptographically signed with the agent's Ethereum key per RFC 9421, creating a verifiable link between HTTP actions and on-chain identity.

## License

Apache-2.0
