# Source-specific nominal stress conversion for Merot small-volume specimens

The nine collision-free small-volume specimens have a different macroscopic stress definition from the standard geometry. Their CSV `s_max` / `s_amp` values match the **local maximum** column of thesis Table G.2, rather than its nominal column. They must not silently enter a nominal-stress benchmark at their raw stress values.

Independent source checks used the primary thesis, including a rendered inspection of Table G.2 (PDF page 280, printed page 256). Thesis section 2.5.2.1 (PDF pages 111–113, printed 87–89) describes measurement of each specimen's polished geometry and a separate axisymmetric, linear-elastic FE calculation for each specimen. Equation 2.3 defines its stress concentration factor. Section 2.5.2.3 (PDF page 115, printed 91) explicitly relates local and nominal stress by `sigma_max = Kt_max * sigma_nom`. Table G.2 preserves specimen-specific nominal/local pairs. The example Kt≈1.18 is **not a universal factor**; the printed ratios of the retained specimens range approximately 1.176–1.289.

The manufactured geometric factor is fixed for the specimen in this linear-elastic stress convention. Applying its ratio at the initial load is a justified inference from the fixed geometry/linear model and the same-specimen stepping protocol; it is not a claim that fatigue damage is absent during later blocks. It uses neither final cycles nor any postfailure defect measurement. Final load values appear only in the ratio that recovers an intrinsic geometric factor, not as additional acquisition features.

For K1, K3, K4, K5, K6 and K8, fracture occurs in the first block, so Table G.2 directly reports their initial nominal stress: respectively 358, 340, 335, 316, 293 and 274 MPa. For K0, K7 and K9, only the first block's survival is retained. Their initial nominal stress is derived as

    nominal_initial = raw_local_initial * (nominal_table / local_table)

This gives 252.2, 273.0 and 252.9230769 MPa, respectively. No later endpoint or equivalent life is used. The original raw values remain available in the crosswalk. These three converted stresses must be labeled derived; the other six are source-reported nominal values.

`small_volume_nominal_stress_crosswalk.csv` retains all nine transcribed pairs, conversion provenance and rounding sensitivities. With exact integer initial local setpoints and conditional nearest-MPa rounding of both displayed Table G.2 stress columns, the derived nominal ranges are K0 [251.6234,252.7778], K7 [272.1469,273.8555], K9 [252.0737,253.7750] MPa. The file also records the wider sensitivity obtained by rounding the initial local input as well. For the six direct entries, the corresponding nearest-MPa sensitivity is ±0.5 MPa.

These intervals are formatting sensitivities conditional on a stated rounding rule, **not measured error bounds or statistical confidence intervals**. The thesis prints integer-MPa stresses without giving a metrological error model. A primary nominal-stress conversion should therefore be frozen before fitting, retain this limitation, and show the raw-local-stress or rounding sensitivity separately. The already normalized 43 standard-geometry nominal records remain an independently valid primary subset even if the nine converted specimens are kept secondary.

The conversion does not change physical identity, initial N, censoring, source family, environment or campaign counts. The three builds represented by the retained first blocks remain one author campaign. Files belonging to other agents were not edited by this audit.
