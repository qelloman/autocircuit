"""
Circuit optimization parameters — the file the LLM modifies.
This is the analog circuit equivalent of autoresearch's train.py.

Usage: uv run optimize.py
"""

from prepare import (
    run_simulation,
    extract_metrics,
    update_pareto,
    load_pareto,
    save_pareto,
    print_summary,
)

# ---------------------------------------------------------------------------
# Circuit parameters (modify these to experiment)
# ---------------------------------------------------------------------------

PARAMS = {
    # First stage: differential input pair (NMOS)
    "M1_W": 10e-6,     # Input diff pair width (m)
    "M1_L": 1e-6,      # Input diff pair length (m)

    # First stage: active load (PMOS current mirror)
    "M3_W": 20e-6,     # PMOS load width (m)
    "M3_L": 1e-6,      # PMOS load length (m)

    # Tail current source
    "M5_W": 10e-6,     # Tail current source width (m)
    "M5_L": 1e-6,      # Tail current source length (m)

    # Second stage: NMOS driver
    "M6_W": 5e-6,      # Second stage NMOS width (m)
    "M6_L": 0.5e-6,    # Second stage NMOS length (m)

    # Second stage: PMOS load (sizing for reference, current set by Ibias2)
    "M7_W": 10e-6,     # Second stage PMOS width (m) — unused with ideal I7
    "M7_L": 0.5e-6,    # Second stage PMOS length (m) — unused with ideal I7

    # Compensation
    "Cc": 2e-12,       # Miller compensation capacitor (F)

    # Bias
    "Ibias": 20e-6,    # First stage bias current (A)
    "Ibias2": 200e-6,  # Second stage bias current (A)
}

# ---------------------------------------------------------------------------
# Run simulation and evaluate
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sim_output = run_simulation(PARAMS)
    metrics = extract_metrics(sim_output)

    if "error" in metrics:
        print(f"Simulation failed: {metrics['error']}")
        print("---")
        print(f"gain_db:       0.00")
        print(f"gbw_hz:        0.00e+00")
        print(f"pm_deg:        0.00")
        print(f"power_w:       0.00e+00")
        print(f"is_pareto:     False")
        print(f"pareto_size:   {len(load_pareto())}")
        print("---")
    else:
        front = load_pareto()
        entry = {**metrics, "params": PARAMS}
        front, is_pareto = update_pareto(entry, front)
        save_pareto(front)
        print_summary(metrics, is_pareto)
