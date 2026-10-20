# RBF109365: separate reported-point collection

[Aghayar et al., DOI 10.1016/j.ijfatigue.2025.109365](https://www.sciencedirect.com/science/article/pii/S0142112325005626), Table 1 supplies **67 individual reported points: 63 failures and 4 runouts**. The four groups contain 25/19/11/12 points (25 °C as-built, 25 °C HIP, 450 °C HIP, 450 °C as-built).

Section 3.4.1 explicitly reuses the 25 °C as-built reference curve from [Behvar et al., DOI 10.1016/j.ijfatigue.2024.108491](https://doi.org/10.1016/j.ijfatigue.2024.108491). Thus 42 points remain outside that reused 25-point curve; 42 is not a verified independent-specimen count. Both publications share a source-family block.

Methods 2.3 identifies nominal rotating-bending stress amplitude, R = −1, and defines runout as “survival without fracture to N ≥ 5.0 × 10^6 cycles”. Individual exact runout stops remain unknown. The 140 MPa, 450 °C as-built failure at 6.07e6 is retained as failure beyond the nominal runout threshold; this does not establish an error or mandatory termination contradiction.

Current-paper methods describe two temperature-specific plates, stress relief 550 °C/6 h, HIP 1150 °C/100 MPa/4 h, and polishing. No author specimen/plate/powder IDs or point crosswalks were recovered. Prior-curve processing is left unverified. Frequency and per-specimen virgin exposure remain unknown.

Publisher-indexed primary text supplied the table; direct HTML/PDF returned 403, and Elsevier API supplied only metadata. License: CC BY-NC-ND 4.0. No supplement was acquired. These exact table transcriptions remain a **separate RBF catalog**, with zero additions to current fits or gold axial cohorts.

Recreate CSVs: `python3 literature/v4_open/rbf2026/normalize_table1.py`.
