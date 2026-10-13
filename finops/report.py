"""Report assembly — the lab's deliverable: baseline vs optimized + savings chart."""
from __future__ import annotations


def build_report(baseline_usd: float, optimized_usd: float, levers: dict,
                 sustainability: dict | None = None, period: str = "monthly",
                 sections: list[str] | None = None) -> str:
    """Return a markdown cost-optimization report."""
    savings = baseline_usd - optimized_usd
    pct = (savings / baseline_usd * 100.0) if baseline_usd > 0 else 0.0
    lines = [
        "# NimbusAI — GPU Cost Optimization Report",
        "",
        f"**Period:** {period}",
        "",
        f"**Baseline spend:** ${baseline_usd:,.0f}",
        "",
        f"**Optimized spend:** ${optimized_usd:,.0f}",
        "",
        f"**Projected savings:** ${savings:,.0f}  (**{pct:.0f}%**)",
        "",
        "## Savings by lever",
        "",
        "| Lever | Savings (USD) |",
        "|---|---|",
    ]
    for name, amount in levers.items():
        lines.append(f"| {name} | ${amount:,.0f} |")
    if sustainability:
        lines += [
            "",
            "## Sustainability",
            "",
            f"- Energy per query: {sustainability.get('wh_per_query', 0):.2f} Wh",
            f"- Carbon per query: {sustainability.get('carbon_g', 0):.3f} gCO2e",
            f"- Lowest-carbon region: {sustainability.get('best_region', 'n/a')}",
        ]
    if sections:
        lines.extend(["", *sections])
    lines += ["", "_Figures are June-2026 as-of snapshots; re-baseline before acting._"]
    return "\n".join(lines)


def savings_waterfall(levers: dict, path: str, baseline_usd: float | None = None) -> str:
    """Write a baseline-to-optimized waterfall PNG; no-op if matplotlib absent."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return ""
    names = list(levers.keys())
    start = baseline_usd if baseline_usd is not None else sum(levers.values())
    remaining = start
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.bar(0, start, color="#5c6770")
    ax.text(0, start, f"${start:,.0f}", ha="center", va="bottom")
    for index, name in enumerate(names, 1):
        amount = levers[name]
        remaining -= amount
        ax.bar(index, amount, bottom=remaining, color="#277da1")
        ax.text(index, remaining + amount / 2, f"−${amount:,.0f}",
                ha="center", va="center", color="white", fontsize=9, fontweight="bold")
        ax.plot([index - 0.6, index - 0.4], [remaining + amount] * 2,
                color="#8a8f93", linewidth=1)
    ax.bar(len(names) + 1, remaining, color="#43aa8b")
    ax.text(len(names) + 1, remaining, f"${remaining:,.0f}", ha="center", va="bottom")
    ax.set_xticks(range(len(names) + 2), ["Baseline", *names, "Optimized"])
    ax.set_ylabel("USD / 30-day window")
    ax.set_title("GPU FinOps: baseline to optimized spend")
    ax.set_ylim(0, start * 1.12)
    ax.grid(axis="y", alpha=0.2)
    ax.set_axisbelow(True)
    plt.xticks(rotation=16, ha="right")
    plt.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path
