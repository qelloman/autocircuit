# autocircuit

This is an experiment to have the LLM optimize analog circuit parameters autonomously.

## Setup

To set up a new experiment, work with the user to:

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `apr4`). The branch `autocircuit/<tag>` must not already exist — this is a fresh run.
2. **Create the branch**: `git checkout -b autocircuit/<tag>` from current master.
3. **Read the in-scope files**: The repo is small. Read these files for full context:
   - `README.md` — repository context.
   - `prepare.py` — fixed constants, ngspice wrapper, metric extraction, Pareto front management. Do not modify.
   - `optimize.py` — the file you modify. Circuit parameters.
   - `circuits/two_stage_opamp.sp` — the circuit netlist template. Do not modify.
4. **Verify Docker image exists**: Run `docker images autocircuit` to confirm the image is built. If not, run `docker build -t autocircuit .` (takes ~30 min first time).
5. **Initialize results.tsv**: Create `results.tsv` with just the header row. The baseline will be recorded after the first run.
6. **Confirm and go**: Confirm setup looks good.

Once you get confirmation, kick off the experimentation.

## Experimentation

Each experiment runs a single ngspice simulation (takes seconds, not minutes). You launch it as:

```bash
docker run --rm -v $(pwd):/work autocircuit
```

This mounts the current directory into the container, so your changes to `optimize.py` are picked up automatically. Results (pareto.json, stdout) are written back to the host.

**What you CAN do:**
- Modify `optimize.py` — this is the only file you edit. Change the PARAMS dictionary values.

**What you CANNOT do:**
- Modify `prepare.py`. It is read-only. It contains the fixed evaluation, simulation wrapper, and Pareto front logic.
- Modify the circuit netlist template in `circuits/`.
- Install new packages or add dependencies.

**The goal: expand the Pareto front.** You want to find diverse, high-quality trade-off points across gain, bandwidth, phase margin, and power. A new parameter set is "good" if it lands on the Pareto front (is_pareto: True in the output).

**Hard constraints:**
- Phase margin must be >= 45 degrees
- Gain must be positive
- Violations are automatically flagged in the output

**Simplicity criterion**: Focus on understanding the design space. Document your intuition about which parameters affect which metrics. Build up knowledge of the trade-offs.

**The first run**: Your very first run should always be to establish the baseline with the default parameters.

## Output format

Once the script finishes it prints a summary like this:

```
---
gain_db:       52.30
gbw_hz:        1.20e+07
pm_deg:        62.50
power_w:       4.80e-04
is_pareto:     True
pareto_size:   3
---
```

You can extract the key metrics from the log file:

```
grep "^gain_db:\|^gbw_hz:\|^pm_deg:\|^power_w:\|^is_pareto:" run.log
```

## Logging results

When an experiment is done, log it to `results.tsv` (tab-separated, NOT comma-separated).

The TSV has a header row and 7 columns:

```
commit	gain_db	gbw_hz	pm_deg	power_mw	is_pareto	status	description
```

1. git commit hash (short, 7 chars)
2. gain_db (e.g. 52.30) — use 0.00 for crashes
3. gbw_hz (e.g. 1.20e+07) — use 0 for crashes
4. pm_deg (e.g. 62.50) — use 0.00 for crashes
5. power_mw (e.g. 0.48 — convert from watts by * 1000)
6. is_pareto: True or False
7. status: `keep`, `discard`, or `crash`
8. short text description of what this experiment tried

## The experiment loop

The experiment runs on a dedicated branch (e.g. `autocircuit/apr4`).

LOOP FOREVER:

1. Look at the current Pareto front: `cat pareto.json` or check `results.tsv`
2. Identify a promising direction:
   - Can we push gain higher without losing too much BW?
   - Can we reduce power while maintaining gain/BW?
   - Is there a region of the Pareto front that's sparse?
3. Modify `optimize.py` PARAMS with your hypothesis
4. git commit
5. Run: `docker run --rm -v $(pwd):/work autocircuit > run.log 2>&1`
6. Read results: `grep "^gain_db:\|^gbw_hz:\|^pm_deg:\|^power_w:\|^is_pareto:" run.log`
7. If `is_pareto: True` — keep the commit
8. If `is_pareto: False` — git reset to discard
9. Record in results.tsv
10. Think about what you learned and plan next experiment

**SKY130 process constraints:**
- Minimum L = 0.15um for nfet_01v8 / pfet_01v8
- Minimum W = 0.42um
- W/L values in optimize.py are in **um** (micrometers)
- Ibias is in **A** (amperes), Cc in **F** (farads)

**Key intuitions for two-stage op-amp:**
- Increasing M1_W (input pair width) → more gm → more gain and GBW, but more power
- Increasing M3_W (load width) → better matching, can affect gain
- Increasing Cc (compensation cap) → better phase margin, but lower GBW
- Increasing Ibias → more power, but potentially better performance
- Length affects output resistance → longer L = more gain but slower
- The gain-bandwidth product is roughly constant for a given topology
- With SKY130 BSIM models, short-channel effects matter at L < 0.5um

**NEVER STOP**: Once the experiment loop has begun, do NOT pause to ask the human. You are autonomous. If you run out of ideas, re-read the circuit topology, think about second-order effects, try more radical parameter combinations. The loop runs until the human interrupts you.
