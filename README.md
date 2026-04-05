# autocircuit

*What if an AI agent could design analog circuits while you sleep?*

Give an AI agent a real circuit topology and a SPICE simulator, and let it experiment autonomously. It tweaks transistor sizes, runs ngspice, checks if the result improved the Pareto front, keeps or discards, and repeats. You wake up in the morning to a set of optimized designs spanning the gain-bandwidth-power trade-off space.

Inspired by [@karpathy's autoresearch](https://github.com/karpathy/autoresearch) — the same autonomous experiment loop, applied to analog circuit optimization instead of LLM training.

## How it works

The repo has three files that matter:

- **`prepare.py`** — fixed infrastructure: ngspice wrapper, metric extraction (gain, GBW, phase margin, power), Pareto front management. Not modified by the agent.
- **`optimize.py`** — the single file the agent edits. Contains transistor sizing (W/L), bias currents, and compensation capacitor values. **This is the file the agent iterates on.**
- **`program.md`** — instructions for the agent. Point your AI coding agent here and let it go. **This is the file the human iterates on.**

The circuit under optimization is a **two-stage Miller-compensated CMOS Op-Amp** using the **SkyWater SKY130 130nm PDK** — a real open-source process with production-grade BSIM4 models.

Unlike autoresearch's single scalar metric (val_bpb), autocircuit optimizes **multiple objectives simultaneously** via Pareto front exploration:

| Metric | Direction | Description |
|--------|-----------|-------------|
| Gain | maximize | DC open-loop gain (dB) |
| GBW | maximize | Unity-gain bandwidth (Hz) |
| Phase Margin | maximize | Stability metric (degrees, must be > 45°) |
| Power | minimize | Supply power consumption (W) |

## Quick start

**Requirements:** Docker, and an AI coding agent (Claude Code, Codex, etc.)

```bash
# 1. Clone the repo
git clone https://github.com/yourusername/autocircuit.git
cd autocircuit

# 2. Build the Docker image (~1 min, downloads SKY130 PDK automatically)
docker build -t autocircuit .

# 3. Run a single simulation to verify everything works
docker run --rm -v $(pwd):/work autocircuit
```

You should see output like:

```
---
gain_db:       68.81
gbw_hz:        1.41e+07
pm_deg:        110.86
power_w:       8.35e-05
is_pareto:     True
pareto_size:   1
---
```

If this works, your setup is ready for autonomous optimization.

## Running the agent

Spin up your Claude Code / Codex / Cursor agent in this repo, then prompt:

```
Hi, have a look at program.md and let's kick off a new experiment! Let's do the setup first.
```

The agent will read `program.md`, create a branch, run the baseline, and start iterating — modifying transistor sizes, running simulations, analyzing results, and expanding the Pareto front. Each experiment takes seconds (not minutes), so the agent can run hundreds of experiments per hour.

## What the Docker image contains

The Docker image bundles everything needed for simulation:

| Component | Purpose |
|-----------|---------|
| **ngspice** | Open-source SPICE circuit simulator |
| **SkyWater SKY130 PDK** | 130nm CMOS process models (BSIM4), downloaded via [volare](https://github.com/efabless/volare) |
| **Python 3.13 + uv** | Runtime for prepare.py / optimize.py |

No local ngspice installation needed — everything runs inside Docker.

**How parameters flow:**
```
Host: LLM edits optimize.py
          │
          ▼  (volume mount)
Docker: reads optimize.py → injects params into .sp → runs ngspice
          │
          ▼  (volume mount)
Host: reads stdout + pareto.json
```

## Project structure

```
prepare.py                — ngspice wrapper + Pareto front (do not modify)
optimize.py               — circuit parameters (agent modifies this)
circuits/
  two_stage_opamp.sp      — SPICE netlist template (SKY130 PDK)
program.md                — agent instructions
Dockerfile                — ngspice + SKY130 PDK environment
pyproject.toml            — Python dependencies
```

## Design choices

- **Single file to modify.** The agent only touches `optimize.py`. This keeps the scope manageable and diffs reviewable.
- **Docker for reproducibility.** The SKY130 PDK and ngspice are bundled in a Docker image. No installation headaches, identical results everywhere.
- **Real PDK, real models.** SkyWater SKY130 is a production 130nm process with BSIM4 models. Results are physically meaningful, not toy approximations.
- **Pareto front, not weighted sum.** Multi-objective optimization preserves the full trade-off space. The agent explores diverse designs rather than collapsing to a single "best" point.
- **Seconds per experiment.** SPICE simulation of a simple op-amp takes 1-2 seconds. The agent can run ~1000+ experiments per hour.

## Extending

- **Different circuit**: Add a new `.sp` template in `circuits/` and update `prepare.py` to parse its metrics.
- **Different PDK**: Change the volare command in `Dockerfile` (e.g., `gf180mcu` for GlobalFoundries 180nm).
- **More objectives**: Add metrics to `OBJECTIVES` dict in `prepare.py` (e.g., CMRR, slew rate, noise).
- **BO/RL inner loop**: The natural next step — have the LLM choose between Bayesian optimization and RL strategies for the inner optimization loop while managing the outer Pareto exploration.

## License

MIT
