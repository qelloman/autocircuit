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
    # First stage: NMOS differential input pair
    "M1_W": 5,         # Input diff pair width (um)
    "M1_L": 1.0,       # Input diff pair length (um)

    # First stage: PMOS active load (current mirror)
    "M3_W": 10,        # PMOS load width (um) — ~2× input pair
    "M3_L": 1.0,       # PMOS load length (um)

    # Bias mirror / tail current source (M0 & M5 share this sizing)
    "M5_W": 2,         # Tail current source width (um)
    "M5_L": 1,         # Tail current source length (um)

    # Second stage: NMOS current sink (load, mirrors Iref via nbias)
    # I_M6 = Ibias × (M6_W/M6_L) / (M5_W/M5_L) = 20u × (4/1)/(2/1) = 40uA
    "M6_W": 4,         # Second stage NMOS current sink width (um)
    "M6_L": 1.0,       # Second stage NMOS current sink length (um)

    # Second stage: PMOS common-source driver (gate driven by 1st stage output)
    "M7_W": 20,        # Second stage PMOS driver width (um)
    "M7_L": 0.5,       # Second stage PMOS driver length (um)

    # Compensation
    "Cc": 2.5e-12,     # Miller compensation capacitor (F) — 2.5pF

    # Bias
    "Ibias": 20e-6,    # Reference bias current (A) — 20μA
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
