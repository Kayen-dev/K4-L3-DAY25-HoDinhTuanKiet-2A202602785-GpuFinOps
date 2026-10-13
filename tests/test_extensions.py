"""Checks for the two optional, measured lab extensions."""
from missions.m2_inference_levers import reasoning_cap_scenario
from missions.m3_purchasing import carbon_schedule


def test_reasoning_cap_only_downgrades_calls_above_limit():
    rows = [(1.0, 10.0), (3.0, 30.0), (2.0, 20.0)]
    loose = reasoning_cap_scenario(rows, 10, 0.5)
    strict = reasoning_cap_scenario(rows, 10, 0.1)
    assert loose["downgraded"] == 0
    assert strict["allowed"] == 1
    assert strict["savings_usd"] == 3.0
    assert strict["savings_wh"] == 30.0


def test_carbon_schedule_uses_actual_days_and_only_interruptible_jobs():
    jobs = [
        {"gpu_type": "H100", "hours_per_day": "2", "days": "3", "num_gpus": "2", "interruptible": "1"},
        {"gpu_type": "H100", "hours_per_day": "24", "days": "30", "num_gpus": "1", "interruptible": "0"},
    ]
    result = carbon_schedule(jobs, {"H100": {"watts": "500"}})
    assert result["kwh"] == 6.0
    assert result["eligible_jobs"] == 1
    assert result["cleanest"] == "europe-north1"
    assert result["cheapest"] == "us-east-wa"
    assert abs(result["carbon_saved_kg"] - 2.1) < 1e-9
