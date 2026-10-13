# NimbusAI — GPU Cost Optimization Report

**Period:** monthly

**Baseline spend:** $18,005

**Optimized spend:** $8,848

**Projected savings:** $9,157  (**51%**)

## Savings by lever

| Lever | Savings (USD) |
|---|---|
| Inference (cascade/cache/batch) | $1,212 |
| Purchasing (spot/reserved) | $6,690 |
| Right-size util-lies | $655 |
| Kill idle GPUs | $600 |

## Sustainability

- Energy per query: 0.24 Wh
- Carbon per query: 0.091 gCO2e
- Lowest-carbon region: europe-north1

## Inference unit economics

The 2,400 sampled requests are treated as one day (225,990,810 tokens over 30 days). The same token denominator is used on both sides.

| Metric | Baseline | Optimized |
|---|---:|---:|
| Inference spend / day | $48.87 | $8.48 |
| USD / 1M tokens | $6.488 | $1.126 |
| Inference spend / 30 days | $1,466.10 | $254.40 |

Sequential savings at fixed traffic and token volume (each row starts from the prior row's cost):

| Inference lever | USD / day | USD / 30 days |
|---|---:|---:|
| Cascade | $37.40 | $1,121.96 |
| Cache | $1.20 | $35.89 |
| Batch | $1.79 | $53.84 |

## Efficiency findings and action order

1. Turn off idle instances after jobs finish. The telemetry sample shows $20.00/day of avoidable on-demand hours; set a shutdown timer first.
2. Route simple requests to the small tier, then enable batch for delay-tolerant evals and cache repeated input. The inference table measures each lever without adding overlapping discounts.
3. Use spot with checkpoints for interruptible training and reservations for steady workloads. Check commitment utilization and interruption risk before purchase.
4. Profile high-utilization GPUs before changing their size. For example, gpu-h100-4 is busy almost all the time but produces only about 20% of peak FLOPs. GPU-Util records time with an active kernel; memory stalls, launch overhead, or inefficient kernels can keep it high while throughput stays low. A cheaper GPU is only viable if memory capacity, bandwidth, latency, and completed tokens per hour remain acceptable.

## Extension: reasoning budget (scenario)

Reasoning makes up 201 requests (8.4% of traffic), $1.40/day (16.5% of optimized inference cost), and 29,787.7 Wh/day (94.0% of estimated inference energy).
A 10% traffic cap permits 240 reasoning requests/day and is nonbinding here: $0.00 and 0.0 Wh saved. A 5% cap permits 120 requests/day; downgrading 81 calls yields $0.03/day and 8,795.8 Wh/day of modeled savings. These scenarios assume the generator's 6x output-token and 80x energy multipliers and are excluded from the main waterfall. The calculation downgrades the least costly calls first; a production rule should instead allow reasoning when a tested complexity classifier predicts a quality benefit, then measure answer quality and adjust the threshold.

## Extension: carbon-aware scheduling (scenario)

The 5 interruptible jobs use 1,789.0 kWh at catalog nameplate power over their listed active days. Moving these jobs from us-east-1 to europe-north1 saves 626.2 kgCO2e in this grid model.

| Region | USD / kWh | gCO2e / kWh | Electricity USD | kgCO2e |
|---|---:|---:|---:|---:|
| us-east-1 | $0.120 | 380 | $214.68 | 679.8 |
| us-west-2 | $0.070 | 120 | $125.23 | 214.7 |
| europe-north1 | $0.090 | 30 | $161.01 | 53.7 |
| europe-central2 | $0.180 | 660 | $322.02 | 1,180.7 |
| us-east-wa | $0.055 | 90 | $98.39 | 161.0 |

Lowest electricity cost: us-east-wa ($116.28 below us-east-1). Lowest carbon: europe-north1. Choose a region after checking data locality, training data transfer, GPU availability and user latency. Keep latency-sensitive inference near users.

## Scope and assumptions

The June 2026 prices, grid factors and workloads are illustrative synthetic data. The 30-day scenario combines API-priced inference requests, workload GPU purchasing and telemetry-based fleet opportunities as separate cost pools; these sources are not reconciled to one billing account. The right-size and idle savings may overlap committed GPU hours, so the total waterfall is a planning estimate, not a verified invoice reduction. The carbon table counts electricity only and uses full nameplate GPU power; it does not include cooling, transfer or regional GPU rental premiums. Reconcile billing IDs and measure throughput before committing changes.

_Figures are June-2026 as-of snapshots; re-baseline before acting._