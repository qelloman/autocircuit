"""
Circuit optimization parameters — the file the LLM modifies.
This is the analog circuit equivalent of autoresearch's train.py.

Usage:
  Local:  uv run optimize.py
  Docker: docker run --rm -v $(pwd):/work autocircuit
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
#
# SKY130 PDK notes:
#   - W/L units are in um (micrometers) — e.g., M1_W=2 means 2um
#   - Minimum L for sky130_fd_pr__nfet_01v8 is 0.15um
#   - Minimum W is 0.42um
#   - Current/capacitance values use SI units (A, F)
# ---------------------------------------------------------------------------

PARAMS = {
    # First stage: differential input pair (NMOS)
    "M1_W": 15,        # Input diff pair width (um) — very wide
    "M1_L": 0.5,       # Input diff pair length (um) — short but safe

    # First stage: active load (PMOS current mirror)
    "M3_W": 30,        # PMOS load width (um)
    "M3_L": 0.5,       # PMOS load length (um)

    # Tail current source
    "M5_W": 8,         # Tail current source width (um) — wide for high current
    "M5_L": 0.5,       # Tail current source length (um)

    # Second stage: NMOS driver
    "M6_W": 30,        # Second stage NMOS width (um) — very wide for speed
    "M6_L": 0.15,      # Second stage NMOS length (um) — min for speed

    # Second stage: PMOS load (sizing for reference, current set by Ibias2)
    "M7_W": 10,        # Second stage PMOS width (um) — unused with ideal I7
    "M7_L": 0.15,      # Second stage PMOS length (um) — unused with ideal I7

    # Compensation
    "Cc": 0.15e-12,    # Miller compensation capacitor (F) — very low

    # Bias
    "Ibias": 100e-6,   # First stage bias current (A) — high
    "Ibias2": 250e-6,  # Second stage bias current (A) — high
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
