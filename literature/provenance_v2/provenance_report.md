# Phase 2 provenance audit

Audit: 20 October 2026. Completed before phase-2 model fitting. This audit reviews source methods and publication reuse; it does not certify every digitized point or reconstruct unshared specimen histories.

## Decisions needed before fitting

1. Exclude DOI **10.1016/j.ijfatigue.2021.106552** from an ordinary constant-amplitude lifetime benchmark. Its tests use increasing stress on the same specimen. The database's S-N label and force-control label do not establish constant-amplitude eligibility.
2. Keep all three near-curve publication families together in any broad sensitivity analysis. Exclude them from the stricter methods-screened panel. One family's reuse is now explicitly documented; exact specimen identity remains unavailable.
3. Distinguish `dataset_id` (a database curve) from batch, build, campaign, and specimen. The database does not provide the latter identities. Wood's seven curves, for example, originate from three builds.
4. Use a **methods-verified panel**, not a claim of completely verified physical independence. As of this agent's handoff, eight singleton sources describe appropriate fatigue methods: 256 database rows and 24 curves. Subsequent independent source audits may amend eligibility only before fitting and with recorded evidence.
5. Keep unverified curve selection, inaccessible methods, review-derived series, and mixed LIT/CAT/model-generated curves in quarantine. An abstract that mentions real experiments does not show which markers were extracted.

## Critical correction: Merot et al.

[Author-deposited full text](https://www.researchgate.net/publication/355122937_Observations_on_the_influence_of_process_and_corrosion_related_defects_on_the_fatigue_strength_of_316L_stainless_steel_manufactured_by_Laser_Powder_Bed_Fusion_L-PBF), DOI [10.1016/j.ijfatigue.2021.106552](https://doi.org/10.1016/j.ijfatigue.2021.106552). HAL record: [hal-03689368](https://hal.science/hal-03689368). The uploaded paper itself identifies SAM handle 10985/22075. PDF download was not completed; the author-upload's indexed complete text was inspected.

Section 2.4, printed p7, describes one million cycles per load step and a 25 MPa increase between steps until fracture. Table 3 lists 23 polished, 34 pre-corroded and six EDM-defect specimens: **63 physical specimens**. The primary database contains 42, 39 and 17 points respectively: **98 rows**. Section 3.3.1 explains that empty markers are surviving load steps, and Eqs7-10 apply Basquin/Miner damage equivalence. Therefore these rows cannot be naively interpreted as independent failure/runout lifetimes under a fixed imposed amplitude. A valid future analysis needs specimen IDs and complete loading histories. No claim is made that the original paper handled its stepped tests incorrectly.

**Effect on phase 1:** the old 1,126-row pilot included these 98 rows. Its computations remain reproducible, but its ordinary constant-amplitude survival interpretation is limited by this newly discovered eligibility error. Recomputed phase-2 panels must exclude this source. Do not recycle the old numerical risks as validated constant-amplitude engineering estimates.

## Publication reuse: what is now established

### Family 2: Zhang/process/fatigue — explicit reuse confirmed at publication level

Zhang et al., DOI [10.1016/j.ijfatigue.2019.105194](https://doi.org/10.1016/j.ijfatigue.2019.105194), [Coventry accepted manuscript](https://pure.coventry.ac.uk/ws/files/30301723/Binder3.pdf), PDF p4/printed p3, §2: “The dataset consists of 139 S-N data obtained from the authors’ prior experimental works”. Its references [27,41-43] identify Materials & Design145(2018)42–54, MSEA703(2017)251–261, JOM70(2018)390–395, and IJFatigue121(2019)252–264. Thus the ML paper is not a new independent experimental campaign relative to those sources. Table1 (PDF pp5–6) gives 18 processing/post-processing sets. The JOM source was not present in the primary 37-DOI panel.

The MatDes2018 accepted manuscript, §3.2.4 (PDF p11), additionally uses prior-work [37] results as a confirmation condition; [37] identifies MSEA2017. This documents reuse of information, while the exact digitized row mapping remains numerical correspondence. MATEC201816522006 is linked by near-curve matches; the complete MATEC text was not successfully retrieved in this audit.

**Rule:** group all five previously identified DOIs; retain original raw rows and the linked-coordinate evidence. Never count five papers as five independent campaigns.

### Family 1: Elangeswaran/post-treatment — strong curve correspondence, exact reuse statement unresolved

DOIs: 10.1007/978-3-030-05861-6_36; 10.1016/j.addma.2021.102570; 10.1016/j.ijfatigue.2019.01.013; 10.1016/j.matdes.2020.108962.

The earlier quantitative screen contains complete 11/11 and10/10 correspondences and multiple smaller complete overlaps. The [2020 publisher PDF](https://re.public.polimi.it/retrieve/f20e4057-d42c-488d-9e0a-4a96fd07b986/1-s2.0-S0264127520304962-main.pdf) was inspectable through the web PDF parser, but local download returned403. Its methods describe machined vertically built samples in four thermal states; institutional publication records agree. This is not sufficient to certify which physical specimens were reused in all four papers. The 2022 Additive Manufacturing full text and the conference chapter were not obtained.

**Rule:** conservative family holdout or exclude from strict panel; call this near-curve correspondence, not specimen-confirmed reuse.

### Family 3: Liang/surface/cyclic — strong curve correspondence, specimen identity unresolved

DOIs: 10.1016/j.ijfatigue.2022.106843; 10.1111/ffe.13684. Independent surface-state curves match12/12 and11/11 in the public digitizations. [Author full text for FFE](https://www.researchgate.net/publication/358823418_Correlation_between_microstructure_and_cyclic_behavior_of_316L_stainless_steel_obtained_by_Laser_Powder_Bed_Fusion) describes both strain- and stress-controlled experiments; the four strain-control points were already excluded from phase1. Institutional records are [IJF](https://sam.ensam.eu/handle/10985/22237) and [FFE](https://sam.ensam.eu/handle/10985/22221). HAL large PDF downloads repeatedly ended incomplete; no complete local PDF or original specimen mapping was acquired. Shared authors, machine and processing alone do not prove shared specimens.

**Rule:** keep both publications together or exclude from strict panel.

### Weak Cui edge

The original screen's3/4 correspondence does not establish reuse on its own. A separate phase-2 agent is inspecting full methods and cross-references. Until the consolidated decision is written, quarantine rather than declare independent. This agent's evidence table deliberately leaves specimen identity unconfirmed.

## Eight-source methods screen

All URLs/locators and condition-level raw metadata are in `source_gate.csv` and `data/processed/v2_provenance_condition_ledger.csv`.

| Source DOI | Methods evidence | Remaining boundary |
|---|---|---|
|10.1002/adem.202200751|Original PDF §2.9,Fig10; constant amplitude,R=.1,10Hz; six ordinary316L markers previously independently spotchecked.|Not nitrogen-modified material. Six point checks do not establish all database sources.|
|10.3390/ma13153293|Original PDF/JATS §2.2,Fig3; HCF R=.1,30Hz; nine HCF points previously checked.|Four VHCF points excluded. Literature overlays are separate from study markers.|
|10.1007/s40964-021-00164-8|Author full text §2.3,ASTME466,R=-1,10 or60–70Hz; failure or1e7 runout. Fig4 andTable2 identify four groups and failure/runout symbols.|No raw specimen ID linkage; methods verified, not every coordinate.|
|10.1016/j.jmst.2019.08.047|Publisher full HTML §2.2–2.3: stress-controlled axial,R=-1,30Hz; two laser scanning strategies.|Raw layer rotation0°/67° distinguishes two conditions but is absent from old model features.|
|10.1016/j.msea.2020.140660|Author full text methods explicitly constant load amplitudes; runout1.1e6,some continued3e6. Four surface/orientation groups.|Comparison Fig21 also overlays literature; own groups must be selected. All marker positions not re-digitized.|
|10.1108/13552541311302932|Author full text methods publishedp89: load control,R=.1,50Hz,to1e7; own three surface series inFig4.|Paper's regression counts versus digitized counts are not fully reconciled; missing/overlaid markers remain possible.|
|10.3390/ma12244203|Original JATS §2.1 and2.9: seven condition groups fromthreebuilds; fixedR=.1,20Hz,maximum1e7 withtwo slight extensions.|Condition count is not independent build count. Figure9 own data,Figure10 comparisons.|
|10.3390/ma15186278|Original JATS §2: axial force control,R=.1,30Hz,23°C; Fig11 own EOS/Renishaw SLM series.|Raw database wrongly assigns EOS700°C/2h treatment toRenishawcurvea0577_d003; source says noHT. Correction is supplied separately.|

The underlying observations are approximately digitized. Neither methods review nor good coordinate agreement proves independent specimen sampling, nondifferential digitization error, or random allocation of censoring. Unseen conditions in this retrospective database are not a newly manufactured prospective campaign.

## Artifacts and reproducibility

- `build_evidence.py`: generates source/condition/duplicate ledgers from unchanged raw data and explicit audit decisions.
- `source_gate.csv`: all37primaryDOIs with eligibility/confidence/quarantine reasons.
- `crosspublication_curve_evidence.csv`: all30prior candidate pairs, row links, quantitative tiers and whether the Zhang reuse statement applies.
- `gate_summary.json`: current eight-source counts and table checksum; consolidated root gate may supersede it before fitting.
- `data/processed/v2_provenance_condition_ledger.csv`:120curve identifiers, raw machine/scan-rotation/process sequence and absence of specimen/batch IDs.
- `data/processed/v2_provenance_metadata_corrections.csv`: source-supported Renishaw treatment correction; raw remains unchanged.
- Download manifests retain successful files and failures. Full texts retain original copyrights and must be excluded from shareable archives unless redistribution rights permit them.

## Final pre-fit point corrections and stress-definition checks

The source-supported correction table now also contains **a0554_d006_p004: runout=0 (event=1)**. Wood §3.4.1 explicitly distinguishes the manually stopped XY-M-SR specimen from the extended ZX-SP-NSR specimen that fractured. Figure14 also documents its fracture surface. Keep the digitized lifetime and stress; these remain approximate, and no invented exact specimen-coordinate replacement is made.

Wood Figure9, PDF p12, was rendered and visually inspected. Its vertical axis is explicitly **maximum stress**, so the conversion at R=.1 is amplitude=.45×maximum. Later SEM captions use the symbol sigma_a for numerically matching maximum stresses, an internal notation inconsistency; the clear S-N axis determines this conversion. Two high-stress points and the extended SP point have the expected scale after conversion. Spierings Fig4 caption also explicitly says maximum stress: the reported polished269MPa and machined255MPa runout limits map to approximately121 and115MPa amplitude, consistent with the corresponding database scale. Kedziora's explicitly reported22,762,694-cycle,341MPa EOS point maps to153.45MPa amplitude; the database gives153.166MPa at22.790millioncycles, a0.19%stress discrepancy. These are targeted scale checks, not exhaustive digitization validation.

For Afkhami, source methods explicitly verify R=.1 and constant amplitude, but the figure-axis conversion was not visually resolved before handoff; mark this distinction. For Lai and Yu, R=-1 makes tensile maximum equal amplitude; their source methods support that ratio. Existing Stern/Voloskov independent checks already verified their maximum-to-amplitude conversions. All surviving source disagreements and unverified fields remain limitations, even after source screening.
