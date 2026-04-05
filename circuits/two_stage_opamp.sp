* Two-Stage CMOS Op-Amp — Autocircuit Optimization Target
* Classic Miller-compensated topology
* Parameters injected by prepare.py

* ---- Design parameters ----
.param M1_W=10u M1_L=1u
.param M3_W=20u M3_L=1u
.param M5_W=10u M5_L=1u
.param M6_W=5u M6_L=0.5u
.param M7_W=10u M7_L=0.5u
.param Cc_val=2p
.param Ibias_val=20u
.param Ibias2_val=200u

* ---- Supply ----
VDD vdd 0 DC 1.8

* ---- MOSFET models (Level 1) ----
.model nmod nmos (level=1 vto=0.5 kp=120u gamma=0.4 lambda=0.04 cbd=10f cbs=10f)
.model pmod pmos (level=1 vto=-0.5 kp=60u gamma=0.4 lambda=0.05 cbd=10f cbs=10f)

* ---- Bias current reference ----
Iref vdd nbias {Ibias_val}
M0 nbias nbias 0 0 nmod W={M5_W} L={M5_L}

* ---- First stage ----
* M5: Tail current source (mirrors Iref)
M5 ntail nbias 0 0 nmod W={M5_W} L={M5_L}

* M1, M2: NMOS differential pair
M1 net1 inp ntail 0 nmod W={M1_W} L={M1_L}
M2 net2 inn ntail 0 nmod W={M1_W} L={M1_L}

* M3, M4: PMOS active load (current mirror)
M3 net1 net1 vdd vdd pmod W={M3_W} L={M3_L}
M4 net2 net1 vdd vdd pmod W={M3_W} L={M3_L}

* ---- Second stage ----
* M6: NMOS common-source amplifier
M6 vout net2 0 0 nmod W={M6_W} L={M6_L}

* I7: Ideal current source load (parametric, models a PMOS current source)
I7 vdd vout {Ibias2_val}

* ---- Miller compensation ----
Cc net2 vout {Cc_val}

* ---- Output load ----
CL vout 0 5p

* ---- Input sources ----
Vinp inp 0 DC 0.9 AC 1
Vinn inn 0 DC 0.9

* ---- Analysis ----
.control
op

* Check operating point
let vout_dc = v(vout)
let vnet2_dc = v(net2)

* AC analysis
ac dec 200 1 10G

let gain_mag = db(v(vout))
let gain_ph = 180/PI * cph(v(vout))

let dc_gain_val = gain_mag[0]

* Find 0dB crossing and phase margin
let ugf_val = 0
let pm_val = 0
let found = 0
let idx = 0
let prev = gain_mag[0]
foreach fval $&frequency
  let cur = gain_mag[idx]
  if (prev >= 0) & (cur < 0) & (found = 0)
    let ugf_val = $fval
    let raw_pm = 180 + gain_ph[idx]
    * Normalize PM to 0-360 range
    if raw_pm > 360
      let pm_val = raw_pm - 360
    else
      if raw_pm < 0
        let pm_val = raw_pm + 360
      else
        let pm_val = raw_pm
      end
    end
    let found = 1
  end
  let prev = cur
  let idx = idx + 1
end

* Power from VDD
let pwr = abs(@vdd[i]) * 1.8

echo "=== METRICS ==="
echo "dc_gain = $&dc_gain_val"
echo "ugf = $&ugf_val"
echo "pm = $&pm_val"
echo "power = $&pwr"
echo "vout_dc = $&vout_dc"
echo "=== END ==="
quit
.endc

.end
