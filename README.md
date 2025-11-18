![status](https://img.shields.io/badge/health-healthy-brightgreen)

# TriCloudSentinel — multicloud intrusion demo

TriCloudSentinel is a lightweight multicloud intrusion-score aggregator + automated remediation demo.
Agents (Azure / GCP / IBM) send scored events → Ensemble aggregates & detects anomalies → Safety Gate receives incidents and remediates.

## One-liner
Collects agent event scores, computes short-window averages/anomalies, and auto-remediates suspicious IPs across Azure / GCP / IBM clouds.

## Architecture (quick)
- **agent.py** — multiple agent containers (agent-azure, agent-gcp, agent-ibm). Each posts scored events to the ensemble `/ingest`.
- **ensemble.py** (Flask)
  - `/ingest` — collects scores, keeps last 60s per-IP evidence, computes averages and anomalies, posts incidents via a resilient `post_incident()`.
  - `/metrics/text` — human-friendly snapshot.
  - `/health` — satisfies Docker healthcheck.
- **safety_gate** — receives incidents and performs mock cloud-specific remediation logic (Azure NSG / GCP firewall / IBM ACL).
- **prometheus** — optional: scrapes metrics for observability.

## What it does
- Randomized demo agents produce IP+user+score events.
- Ensemble aggregates scores and flags anomalies (avg > 0.6 + min 2 entries).
- Safety Gate auto-remediates or marks incidents for manual approval.

## Quick setup
From repo root:

```bash
docker compose up -d --force-recreate --build
docker compose ps
