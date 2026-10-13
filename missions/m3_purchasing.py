"""M3 — Purchasing Strategy: break-even, tier choice, spot-checkpoint sim (deck §4).

Run: python missions/m3_purchasing.py
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from missions._common import load_csv, num, catalog_by_type
from finops import pricing, sustainability

def carbon_schedule(jobs: list[dict], cat: dict) -> dict:
    """Compare moving interruptible jobs from us-east-1 across grid regions.

    Energy uses catalog nameplate watts and each job's actual scheduled days.
    The comparison excludes transfer, regional GPU price and latency differences.
    """
    eligible = [j for j in jobs if int(num(j["interruptible"]))]
    kwh = sum(num(cat[j["gpu_type"]]["watts"]) / 1000 *
              num(j["hours_per_day"]) * num(j["days"]) * num(j["num_gpus"])
              for j in eligible)
    regions = []
    for name, intensity in sustainability.REGION_CARBON.items():
        regions.append({"region": name, "usd_per_kwh": sustainability.REGION_PRICE_KWH[name],
                        "gco2_per_kwh": intensity,
                        "electricity_usd": kwh * sustainability.REGION_PRICE_KWH[name],
                        "carbon_kg": kwh * intensity / 1000})
    cheapest = min(regions, key=lambda r: r["electricity_usd"])
    cleanest = min(regions, key=lambda r: r["carbon_kg"])
    origin = next(r for r in regions if r["region"] == "us-east-1")
    return {"eligible_jobs": len(eligible), "kwh": kwh, "regions": regions,
            "cheapest": cheapest["region"], "cleanest": cleanest["region"],
            "carbon_saved_kg": origin["carbon_kg"] - cleanest["carbon_kg"],
            "electricity_saved_usd": origin["electricity_usd"] - cheapest["electricity_usd"]}


def run(verbose: bool = True) -> dict:
    jobs = load_csv("workloads.csv")
    cat = catalog_by_type()
    on_demand_monthly = optimized_monthly = 0.0
    recs = []
    for j in jobs:
        gtype = j["gpu_type"]
        ngpu = int(num(j["num_gpus"]))
        hpd = num(j["hours_per_day"])
        interruptible = bool(int(num(j["interruptible"])))
        c = cat[gtype]
        gpu_hours = hpd * num(j["days"]) * ngpu
        od = num(c["on_demand_hr"])
        on_demand_cost = gpu_hours * od

        tier = pricing.recommend_tier(hpd, interruptible)
        if tier == "spot":
            sim = pricing.spot_checkpoint_cost(gpu_hours, num(c["spot_hr"]), od)
            opt_cost = sim["spot_cost"]
        elif tier == "reserved":
            opt_cost = gpu_hours * num(c["reserved_3yr_hr"])
        else:
            opt_cost = on_demand_cost

        on_demand_monthly += on_demand_cost
        optimized_monthly += opt_cost
        recs.append({"job_id": j["job_id"], "gpu_type": gtype, "tier": tier,
                     "on_demand": round(on_demand_cost), "optimized": round(opt_cost)})

    savings = on_demand_monthly - optimized_monthly
    savings_pct = savings / on_demand_monthly * 100 if on_demand_monthly else 0.0
    schedule = carbon_schedule(jobs, cat)

    if verbose:
        print("== M3 Purchasing Strategy ==")
        print(f"break-even utilization @ 45% reserved discount = {pricing.break_even_utilization(0.45):.0%}")
        print(f"{'job':18}{'gpu':7}{'tier':11}{'on-demand':>12}{'optimized':>12}")
        for r in recs:
            print(f"{r['job_id']:18}{r['gpu_type']:7}{r['tier']:11}${r['on_demand']:>11,}${r['optimized']:>11,}")
        print(f"\nmonthly: on-demand ${on_demand_monthly:,.0f} -> optimized ${optimized_monthly:,.0f}  ({savings_pct:.1f}% saved)")
        print(f"carbon-aware schedule ({schedule['eligible_jobs']} interruptible jobs, {schedule['kwh']:.0f} kWh):")
        for region in schedule["regions"]:
            print(f"  {region['region']:18} ${region['electricity_usd']:,.2f} electricity  "
                  f"{region['carbon_kg']:,.1f} kgCO2e")
        print(f"cleanest: {schedule['cleanest']} ({schedule['carbon_saved_kg']:,.1f} kgCO2e saved); "
              f"cheapest: {schedule['cheapest']} (${schedule['electricity_saved_usd']:,.2f} saved)")

    return {"recommendations": recs, "on_demand_monthly": round(on_demand_monthly),
            "optimized_monthly": round(optimized_monthly), "savings_pct": round(savings_pct, 1),
            "carbon_schedule": schedule}


if __name__ == "__main__":
    run()
