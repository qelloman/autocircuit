* Two-Stage CMOS Op-Amp — Autocircuit Optimization Target
* SkyWater SKY130 PDK (130nm process)
* Parameters injected by prepare.py

* ---- Design parameters ----
.param M1_W=5 M1_L=1
.param M3_W=10 M3_L=1
.param M5_W=2 M5_L=1
.param M6_W=4 M6_L=1
.param M7_W=20 M7_L=0.5
.param Cc_val=1.5p
.param Ibias_val=20u

* ---- SKY130 PDK models ----
.lib /opt/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice tt

* ---- Supply (1.8V for SKY130) ----
VDD vdd 0 DC 1.8

* ---- Bias current reference ----
Iref vdd nbias {Ibias_val}
xM0 nbias nbias 0 0 sky130_fd_pr__nfet_01v8 w={M5_W} l={M5_L}

* ---- First stage ----
* Tail current source (mirrors Iref)
xM5 ntail nbias 0 0 sky130_fd_pr__nfet_01v8 w={M5_W} l={M5_L}

* NMOS differential pair
xM1 net1 inn ntail 0 sky130_fd_pr__nfet_01v8 w={M1_W} l={M1_L}
xM2 net2 inp ntail 0 sky130_fd_pr__nfet_01v8 w={M1_W} l={M1_L}

* PMOS active load (current mirror)
xM3 net1 net1 vdd vdd sky130_fd_pr__pfet_01v8 w={M3_W} l={M3_L}
xM4 net2 net1 vdd vdd sky130_fd_pr__pfet_01v8 w={M3_W} l={M3_L}

* ---- Second stage ----
* NMOS common-source amplifier
xM6 vout nbias 0 0 sky130_fd_pr__nfet_01v8 w={M6_W} l={M6_L}
xM7 vout net2 vdd vdd sky130_fd_pr__pfet_01v8 w={M7_W} l={M7_L}

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

ac dec 200 1 10G

let gain_mag = db(v(vout))
let gain_ph = 180/PI * cph(v(vout))
let dc_gain_val = gain_mag[0]

* Find -3dB bandwidth
let bw3db_val = 0
let bw_found = 0
let bw_thresh = dc_gain_val - 3
let bw_idx = 0
let bw_prev = gain_mag[0]
foreach bwf $&frequency
  let bw_cur = gain_mag[bw_idx]
  if (bw_prev >= bw_thresh) & (bw_cur < bw_thresh) & (bw_found = 0)
    let bw3db_val = $bwf
    let bw_found = 1
  end
  let bw_prev = bw_cur
  let bw_idx = bw_idx + 1
end

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
echo "bw3db = $&bw3db_val"
echo "ugf = $&ugf_val"
echo "pm = $&pm_val"
echo "power = $&pwr"
echo "=== END ==="
quit
.endc

.end
