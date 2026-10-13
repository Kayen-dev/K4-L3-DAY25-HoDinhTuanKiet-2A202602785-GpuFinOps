"""M5 — Optimization Report: combine M1-M4 into baseline-vs-optimized (deck §1/§11).

Run: python missions/m5_report.py   ->  outputs/report.md + outputs/savings.png
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import os
from missions._common import num, catalog_by_type, ROOT
from finops import report, sustainability
from missions import m1_efficiency_audit, m2_inference_levers, m3_purchasing

DAYS = 30
# one tier down for over-provisioned ("util-lie") GPUs
RIGHTSIZE_MAP = {"H100": "A100", "H200": "H100", "A100": "A10G", "A10G": "L4", "L4": "L4"}


def run(verbose: bool = True) -> dict:
    r1 = m1_efficiency_audit.run(verbose=False)
    r2 = m2_inference_levers.run(verbose=False)
    r3 = m3_purchasing.run(verbose=False)
    cat = catalog_by_type()

    # --- buckets ---
    infer_savings = (r2["baseline_daily"] - r2["optimized_daily"]) * DAYS
    purchasing_savings = r3["on_demand_monthly"] - r3["optimized_monthly"]

    idle_savings = r1["idle_waste_daily"] * DAYS
    rightsize_savings = 0.0
    for lie in r1["lies"]:
        cur = lie["gpu_type"]
        tgt = RIGHTSIZE_MAP.get(cur, cur)
        delta = num(cat[cur]["on_demand_hr"]) - num(cat[tgt]["on_demand_hr"])
        rightsize_savings += max(0.0, delta) * 24 * DAYS

    levers = {
        "Inference (cascade/cache/batch)": round(infer_savings),
        "Purchasing (spot/reserved)": round(purchasing_savings),
        "Right-size util-lies": round(rightsize_savings),
        "Kill idle GPUs": round(idle_savings),
    }
    baseline = r2["baseline_daily"] * DAYS + r3["on_demand_monthly"]
    optimized = baseline - sum(levers.values())
    total_pct = sum(levers.values()) / baseline * 100 if baseline else 0.0

    # --- sustainability snapshot ---
    median_tokens = 800
    wh = sustainability.wh_per_query(median_tokens)
    sust = {
        "wh_per_query": wh,
        "carbon_g": sustainability.carbon_g(wh, "us-east-1"),
        "best_region": min(sustainability.REGION_CARBON, key=sustainability.REGION_CARBON.get),
    }

    reason = r2["reasoning"]
    cap10, cap5 = reason["cap_scenarios"]
    schedule = r3["carbon_schedule"]
    inference_breakdown = r2["lever_savings_daily"]
    monthly_tokens = r2["total_tokens"] * DAYS
    sections = [
        "## Inference unit economics",
        "",
        f"The {r2['request_count']:,} sampled requests are treated as one day "
        f"({monthly_tokens:,} tokens over 30 days). The same token denominator is used on both sides.",
        "",
        "| Metric | Baseline | Optimized |",
        "|---|---:|---:|",
        f"| Inference spend / day | ${r2['baseline_daily']:,.2f} | ${r2['optimized_daily']:,.2f} |",
        f"| USD / 1M tokens | ${r2['baseline_per_m']:.3f} | ${r2['optimized_per_m']:.3f} |",
        f"| Inference spend / 30 days | ${r2['baseline_daily']*DAYS:,.2f} | ${r2['optimized_daily']*DAYS:,.2f} |",
        "",
        "Sequential savings at fixed traffic and token volume (each row starts from the prior row's cost):",
        "",
        "| Inference lever | USD / day | USD / 30 days |",
        "|---|---:|---:|",
    ]
    for name, amount in inference_breakdown.items():
        sections.append(f"| {name.title()} | ${amount:,.2f} | ${amount*DAYS:,.2f} |")
    sections += [
        "",
        "## Efficiency findings and action order",
        "",
        "1. Turn off idle instances after jobs finish. The telemetry sample shows "
        f"${r1['idle_waste_daily']:.2f}/day of avoidable on-demand hours; set a shutdown timer first.",
        "2. Route simple requests to the small tier, then enable batch for delay-tolerant evals and "
        "cache repeated input. The inference table measures each lever without adding overlapping discounts.",
        "3. Use spot with checkpoints for interruptible training and reservations for steady workloads. "
        "Check commitment utilization and interruption risk before purchase.",
        "4. Profile high-utilization GPUs before changing their size. For example, gpu-h100-4 is busy "
        "almost all the time but produces only about 20% of peak FLOPs. GPU-Util records time "
        "with an active kernel; memory stalls, launch overhead, or inefficient kernels can keep it high "
        "while throughput stays low. A cheaper GPU is only viable if memory capacity, bandwidth, "
        "latency, and completed tokens per hour remain acceptable.",
        "",
        "## Extension: reasoning budget (scenario)",
        "",
        f"Reasoning makes up {reason['requests']:,} requests ({reason['traffic_pct']:.1f}% of traffic), "
        f"${reason['cost_usd']:.2f}/day ({reason['cost_pct']:.1f}% of optimized inference cost), "
        f"and {reason['wh']:,.1f} Wh/day ({reason['energy_pct']:.1f}% of estimated inference energy).",
        f"A 10% traffic cap permits {int(r2['request_count']*0.10):,} "
        f"reasoning requests/day and is nonbinding here: ${cap10['savings_usd']:.2f} and "
        f"{cap10['savings_wh']:.1f} Wh saved. A 5% cap permits {cap5['allowed']:,} requests/day; "
        f"downgrading {cap5['downgraded']} calls yields ${cap5['savings_usd']:.2f}/day and "
        f"{cap5['savings_wh']:,.1f} Wh/day of modeled savings. These scenarios assume the "
        "generator's 6x output-token and 80x energy multipliers and are excluded from the main "
        "waterfall. The calculation downgrades the least costly calls first; a production rule "
        "should instead allow reasoning when a tested complexity classifier predicts a quality "
        "benefit, then measure answer quality and adjust the threshold.",
        "",
        "## Extension: carbon-aware scheduling (scenario)",
        "",
        f"The {schedule['eligible_jobs']} interruptible jobs use {schedule['kwh']:,.1f} kWh at catalog "
        "nameplate power over their listed active days. Moving these jobs from us-east-1 to "
        f"{schedule['cleanest']} saves {schedule['carbon_saved_kg']:,.1f} kgCO2e in this grid model.",
        "",
        "| Region | USD / kWh | gCO2e / kWh | Electricity USD | kgCO2e |",
        "|---|---:|---:|---:|---:|",
    ]
    for region in schedule["regions"]:
        sections.append(f"| {region['region']} | ${region['usd_per_kwh']:.3f} | "
                        f"{region['gco2_per_kwh']} | ${region['electricity_usd']:,.2f} | "
                        f"{region['carbon_kg']:,.1f} |")
    sections += [
        "",
        f"Lowest electricity cost: {schedule['cheapest']} "
        f"(${schedule['electricity_saved_usd']:,.2f} below us-east-1). "
        f"Lowest carbon: {schedule['cleanest']}. Choose a region after checking data locality, "
        "training data transfer, GPU availability and user latency. Keep latency-sensitive inference near users.",
        "",
        "## Scope and assumptions",
        "",
        "The June 2026 prices, grid factors and workloads are illustrative synthetic data. "
        "The 30-day scenario combines API-priced inference requests, workload GPU purchasing and "
        "telemetry-based fleet opportunities as separate cost pools; these sources are not "
        "reconciled to one billing account. The right-size and idle savings may overlap committed "
        "GPU hours, so the total waterfall is a planning estimate, not a verified invoice reduction. "
        "The carbon table counts electricity only and uses full nameplate GPU power; it does not "
        "include cooling, transfer or regional GPU rental premiums. Reconcile billing IDs and "
        "measure throughput before committing changes.",
    ]
    md = report.build_report(baseline, optimized, levers, sustainability=sust, sections=sections)
    out_md = os.path.join(ROOT, "outputs", "report.md")
    os.makedirs(os.path.dirname(out_md), exist_ok=True)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(md)
    png = report.savings_waterfall(levers, os.path.join(ROOT, "outputs", "savings.png"), baseline)

    if verbose:
        print("== M5 Optimization Report ==")
        print(md)
        print(f"\nWritten: outputs/report.md" + (f" + outputs/savings.png" if png else " (matplotlib absent: PNG skipped)"))

    return {"baseline_monthly": round(baseline), "optimized_monthly": round(optimized),
            "levers": levers, "total_savings_pct": round(total_pct, 1)}


if __name__ == "__main__":
    run()
