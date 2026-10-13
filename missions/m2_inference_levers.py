"""M2 — Inference Cost Levers: $/1M-token, batch x cache x cascade (deck §7).

Run: python missions/m2_inference_levers.py
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from missions._common import load_csv, num
from finops import pricing, sustainability

# $/1M tokens (input, output) — illustrative 2026.
MODEL_PRICES = {"small": (0.20, 0.40), "large": (3.00, 15.00)}
REASONING_CAPS = (0.10, 0.05)


def reasoning_cap_scenario(reasoning_rows: list[tuple[float, float]], total_requests: int,
                           cap: float) -> dict:
    """Downgrade cheapest-to-change reasoning calls until a traffic cap is met."""
    allowed = min(len(reasoning_rows), int(total_requests * cap))
    downgraded = sorted(reasoning_rows, key=lambda pair: pair[0])[:len(reasoning_rows) - allowed]
    return {"cap_pct": cap * 100, "allowed": allowed,
            "downgraded": len(downgraded),
            "savings_usd": sum(item[0] for item in downgraded),
            "savings_wh": sum(item[1] for item in downgraded)}


def run(verbose: bool = True) -> dict:
    rows = load_csv("token_usage.csv")
    base_cost = opt_cost = cascade_cost = cache_cost = 0.0
    total_tokens = 0
    reasoning = {False: {"requests": 0, "cost": 0.0, "wh": 0.0},
                 True: {"requests": 0, "cost": 0.0, "wh": 0.0}}
    reasoning_rows = []
    for r in rows:
        inp, out = int(num(r["input_tokens"])), int(num(r["output_tokens"]))
        cached = int(num(r["cached_input_tokens"]))
        is_batch = bool(int(num(r["is_batch"])))
        total_tokens += inp + out
        # BASELINE: naive deployment — everything on the large model, no cache, no batch
        lin, lout = MODEL_PRICES["large"]
        base_cost += pricing.request_cost(inp, out, lin, lout)
        # OPTIMIZED: cascade (route_tier), prompt caching, batch API
        pin, pout = MODEL_PRICES[r["route_tier"]]
        routed = pricing.request_cost(inp, out, pin, pout)
        cached_cost = pricing.request_cost(inp, out, pin, pout, cached_in=cached)
        final_cost = pricing.request_cost(inp, out, pin, pout, cached_in=cached, batch=is_batch)
        cascade_cost += routed
        cache_cost += cached_cost
        opt_cost += final_cost
        is_reasoning = bool(int(num(r["is_reasoning"])))
        group = reasoning[is_reasoning]
        group["requests"] += 1
        group["cost"] += final_cost
        request_wh = sustainability.wh_per_query(inp + out, is_reasoning=is_reasoning)
        group["wh"] += request_wh
        if is_reasoning:
            standard_out = round(out / 6)  # generator's reasoning output multiplier
            standard_cost = pricing.request_cost(inp, standard_out, pin, pout,
                                                 cached_in=cached, batch=is_batch)
            standard_wh = sustainability.wh_per_query(inp + standard_out)
            reasoning_rows.append((final_cost - standard_cost, request_wh - standard_wh))

    # Cost-minimizing scenario; production routing requires a quality classifier.
    cap_scenarios = [reasoning_cap_scenario(reasoning_rows, len(rows), cap)
                     for cap in REASONING_CAPS]

    base_pm = pricing.dollars_per_million(base_cost, total_tokens)
    opt_pm = pricing.dollars_per_million(opt_cost, total_tokens)
    savings_pct = (1 - opt_cost / base_cost) * 100 if base_cost else 0.0
    breakdown = {"cascade": base_cost - cascade_cost,
                 "cache": cascade_cost - cache_cost,
                 "batch": cache_cost - opt_cost}
    reason_total_cost = sum(group["cost"] for group in reasoning.values())
    reason_total_wh = sum(group["wh"] for group in reasoning.values())
    reason_summary = {
        "requests": reasoning[True]["requests"],
        "traffic_pct": 100 * reasoning[True]["requests"] / len(rows) if rows else 0.0,
        "cost_usd": reasoning[True]["cost"],
        "cost_pct": 100 * reasoning[True]["cost"] / reason_total_cost if reason_total_cost else 0.0,
        "wh": reasoning[True]["wh"],
        "energy_pct": 100 * reasoning[True]["wh"] / reason_total_wh if reason_total_wh else 0.0,
        "cap_scenarios": cap_scenarios,
    }

    if verbose:
        print("== M2 Inference Cost Levers ==")
        print(f"requests={len(rows)}  tokens={total_tokens:,}")
        print(f"baseline  : ${base_cost:,.2f}/day   ${base_pm:.3f}/1M-token")
        print(f"optimized : ${opt_cost:,.2f}/day   ${opt_pm:.3f}/1M-token")
        print(f"savings   : {savings_pct:.1f}%  (cascade + caching + batch)")
        print("lever savings ($/day): " + ", ".join(f"{k} ${v:.2f}" for k, v in breakdown.items()))
        print(f"reasoning: {reason_summary['traffic_pct']:.1f}% traffic, {reason_summary['cost_pct']:.1f}% cost, "
              f"{reason_summary['energy_pct']:.1f}% energy")
        for scenario in cap_scenarios:
            print(f"{scenario['cap_pct']:.0f}% reasoning cap: downgrade {scenario['downgraded']} requests, "
                  f"save ${scenario['savings_usd']:.2f}/day and {scenario['savings_wh']:.1f} Wh/day")
        print(f"discount stack (batch + 100% cache): {pricing.discount_stack(batch=True, cache_hit_frac=1.0):.3f} of naive")

    return {
        "baseline_daily": round(base_cost, 2), "optimized_daily": round(opt_cost, 2),
        "baseline_per_m": round(base_pm, 3), "optimized_per_m": round(opt_pm, 3),
        "savings_pct": round(savings_pct, 1), "total_tokens": total_tokens,
        "request_count": len(rows),
        "lever_savings_daily": breakdown, "reasoning": reason_summary,
    }


if __name__ == "__main__":
    run()
