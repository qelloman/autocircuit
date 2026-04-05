"""
Fixed infrastructure for autocircuit — DO NOT MODIFY.
Provides: ngspice simulation wrapper, metric extraction, Pareto front management.

This is the analog circuit equivalent of autoresearch's prepare.py.
"""

import json
import os
import re
import subprocess
import tempfile

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CIRCUIT_DIR = os.path.join(os.path.dirname(__file__), "circuits")
TEMPLATE_FILE = os.path.join(CIRCUIT_DIR, "two_stage_opamp.sp")
PARETO_FILE = os.path.join(os.path.dirname(__file__), "pareto.json")

# Objectives: name -> direction ("max" or "min")
OBJECTIVES = {
    "gain_db": "max",
    "gbw_hz": "max",
    "pm_deg": "max",
    "power_w": "min",
}

# Hard constraints (violating these = automatic discard)
CONSTRAINTS = {
    "pm_deg": (">=", 45.0),     # Phase margin must be >= 45 degrees
    "gain_db": (">", 0.0),      # Must have positive gain
}

# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def _format_spice_value(val):
    """Convert Python float to SPICE-compatible string.

    For SKY130: W/L params are in um (plain numbers like 2, 0.5).
    For current/capacitance: use SI suffixes (u, p, etc).
    """
    abs_val = abs(val)
    if abs_val == 0:
        return "0"
    elif abs_val >= 0.01:
        # Plain number (for W/L in um, or any value >= 0.01)
        return f"{val:.6g}"
    elif abs_val >= 1e-3:
        return f"{val*1e3:.4g}m"
    elif abs_val >= 1e-6:
        return f"{val*1e6:.4g}u"
    elif abs_val >= 1e-9:
        return f"{val*1e9:.4g}n"
    elif abs_val >= 1e-12:
        return f"{val*1e12:.4g}p"
    elif abs_val >= 1e-15:
        return f"{val*1e15:.4g}f"
    else:
        return f"{val:.6g}"


def _inject_params(template_text, params):
    """Replace .param values in SPICE netlist template."""
    # Map from optimize.py param names to SPICE .param names
    param_map = {
        "M1_W": "M1_W", "M1_L": "M1_L",
        "M3_W": "M3_W", "M3_L": "M3_L",
        "M5_W": "M5_W", "M5_L": "M5_L",
        "M6_W": "M6_W", "M6_L": "M6_L",
        "M7_W": "M7_W", "M7_L": "M7_L",
        "Cc": "Cc_val",
        "Ibias": "Ibias_val",
        "Ibias2": "Ibias2_val",
    }
    lines = template_text.split("\n")
    new_lines = []
    for line in lines:
        if line.strip().startswith(".param"):
            for py_name, spice_name in param_map.items():
                if py_name in params and spice_name in line:
                    # Replace value for this param
                    pattern = rf"({spice_name}\s*=\s*)\S+"
                    replacement = rf"\g<1>{_format_spice_value(params[py_name])}"
                    line = re.sub(pattern, replacement, line)
            new_lines.append(line)
        else:
            new_lines.append(line)
    return "\n".join(new_lines)


def run_simulation(params):
    """
    Inject params into circuit template and run ngspice.
    Returns: dict with raw stdout/stderr from ngspice.
    """
    with open(TEMPLATE_FILE, "r") as f:
        template = f.read()

    netlist = _inject_params(template, params)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".sp", delete=False) as f:
        f.write(netlist)
        tmp_path = f.name

    try:
        result = subprocess.run(
            ["ngspice", "-b", tmp_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "netlist": netlist,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "TIMEOUT", "returncode": -1, "netlist": netlist}
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Metric extraction
# ---------------------------------------------------------------------------

def _parse_ngspice_value(text, var_name):
    """Extract a numeric value from ngspice print output."""
    # ngspice prints like: "dc_gain = 5.234000e+01" or "dc_gain = 52.34"
    patterns = [
        rf"{var_name}\s*=\s*([+-]?[\d.]+[eE][+-]?\d+)",
        rf"{var_name}\s*=\s*([+-]?[\d.]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return float(match.group(1))
    return None


def extract_metrics(sim_output):
    """
    Parse ngspice output to extract circuit performance metrics.
    Returns: dict with gain_db, gbw_hz, pm_deg, power_w.
    """
    stdout = sim_output.get("stdout", "")
    stderr = sim_output.get("stderr", "")
    combined = stdout + "\n" + stderr

    # Check for simulation errors
    if sim_output.get("returncode", -1) != 0 and "TIMEOUT" in stderr:
        return {"error": "simulation timeout"}

    dc_gain = _parse_ngspice_value(combined, "dc_gain")
    ugf = _parse_ngspice_value(combined, "ugf")
    pm = _parse_ngspice_value(combined, "pm")
    power = _parse_ngspice_value(combined, "power")

    # Normalize phase margin to 0-180 range
    if pm is not None:
        # ngspice cph() gives cumulative phase; PM = 180 + phase(at UGF)
        # Normalize: wrap into 0-360 then cap at 180
        pm_normalized = pm % 360
        if pm_normalized > 180:
            pm_normalized = 360 - pm_normalized
    else:
        pm_normalized = 0.0

    metrics = {
        "gain_db": dc_gain if dc_gain is not None else 0.0,
        "gbw_hz": ugf if ugf is not None else 0.0,
        "pm_deg": pm_normalized,
        "power_w": power if power is not None else 0.0,
    }

    return metrics


# ---------------------------------------------------------------------------
# Pareto front management
# ---------------------------------------------------------------------------

def _dominates(a, b):
    """Returns True if point a dominates point b (a is better in all objectives, strictly in at least one)."""
    dominated_all = True
    strictly_better = False
    for obj, direction in OBJECTIVES.items():
        a_val, b_val = a.get(obj, 0), b.get(obj, 0)
        if direction == "max":
            if a_val < b_val:
                dominated_all = False
            if a_val > b_val:
                strictly_better = True
        else:  # min
            if a_val > b_val:
                dominated_all = False
            if a_val < b_val:
                strictly_better = True
    return dominated_all and strictly_better


def _satisfies_constraints(point):
    """Check if a point satisfies all hard constraints."""
    for metric, (op, threshold) in CONSTRAINTS.items():
        val = point.get(metric, 0)
        if op == ">=" and val < threshold:
            return False
        if op == ">" and val <= threshold:
            return False
        if op == "<=" and val > threshold:
            return False
        if op == "<" and val >= threshold:
            return False
    return True


def update_pareto(new_point, front):
    """
    Check if new_point is Pareto-optimal and update front.
    Returns: (updated_front, is_pareto_optimal)
    """
    # Check constraints first
    if not _satisfies_constraints(new_point):
        return front, False

    # Check if new point is dominated by any existing point
    for p in front:
        if _dominates(p, new_point):
            return front, False

    # New point is not dominated — add it and remove any points it dominates
    new_front = [p for p in front if not _dominates(new_point, p)]
    new_front.append(new_point)

    return new_front, True


def load_pareto():
    """Load Pareto front from JSON file."""
    if not os.path.exists(PARETO_FILE):
        return []
    with open(PARETO_FILE, "r") as f:
        return json.load(f)


def save_pareto(front):
    """Save Pareto front to JSON file."""
    with open(PARETO_FILE, "w") as f:
        json.dump(front, f, indent=2)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_summary(metrics, is_pareto):
    """Print results in machine-readable format (like autoresearch's val_bpb output)."""
    front = load_pareto()
    print("---")
    print(f"gain_db:       {metrics.get('gain_db', 0):.2f}")
    print(f"gbw_hz:        {metrics.get('gbw_hz', 0):.2e}")
    print(f"pm_deg:        {metrics.get('pm_deg', 0):.2f}")
    print(f"power_w:       {metrics.get('power_w', 0):.2e}")
    print(f"is_pareto:     {is_pareto}")
    print(f"pareto_size:   {len(front)}")

    # Check constraint violations
    violated = []
    for metric, (op, threshold) in CONSTRAINTS.items():
        val = metrics.get(metric, 0)
        if op == ">=" and val < threshold:
            violated.append(f"{metric} = {val:.2f} (need {op} {threshold})")
        elif op == ">" and val <= threshold:
            violated.append(f"{metric} = {val:.2f} (need {op} {threshold})")
    if violated:
        print(f"violations:    {'; '.join(violated)}")

    print("---")


# ---------------------------------------------------------------------------
# Main (for standalone testing)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Quick test with default params
    default_params = {
        "M1_W": 2, "M1_L": 0.5,       # um
        "M3_W": 4, "M3_L": 0.5,       # um
        "M5_W": 2, "M5_L": 1,         # um
        "M6_W": 5, "M6_L": 0.15,      # um
        "M7_W": 10, "M7_L": 0.15,     # um
        "Cc": 1e-12, "Ibias": 20e-6, "Ibias2": 100e-6,
    }
    print("Running test simulation...")
    sim = run_simulation(default_params)
    print(f"ngspice return code: {sim['returncode']}")
    metrics = extract_metrics(sim)
    print(f"Extracted metrics: {metrics}")
