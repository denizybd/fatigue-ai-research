# Merot primary-source handoff

**Usable source recovery:**70physically unique first recorded blocks, spanning one author research program and three actual production builds.52are air at20°C. Of these,43have nominal gauge stress;9small-volume specimens have local peak stress.18salt-spray records remain separate. This source work ran no models.

**Public data license:** Pierre Merot, Linamaria Gallegos Mayorga, Franck Morel, Etienne Pessard, Paul Buttin and Thierry Baffie, *316L L-PBF fatigue dataset*, version1,16June2022, DOI10.5281/zenodo.6653187. Producer metadata declares **CC BY4.0** (`cc-by-4.0`); preserve attribution, DOI, the license link https://creativecommons.org/licenses/by/4.0/ and an indication that rows were filtered to initial blocks and joined to documented physical-build metadata. Raw file MD5 matches the producer's18785df9588f397a5c7f37756730704c. SHA256bb5e9ce46a7f7827aef50f2188f059c6833ca3dab9110cec1613c628a2e16b5e. Raw public URL: https://zenodo.org/api/records/6653187/files/data_fatigue_merot.csv/content .

**Thesis permission differs:** Pierre Merot, *Effet des défauts de fabrication et de corrosion sur le comportement en fatigue d'un acier316L obtenu par fabrication additive*, HESAM2021, NNT2021HESAE076, tel-03688021v1. Repository metadata labels this **Autorisation HAL**, linking https://about.hal.science/hal-authorisation-v1/ . A broad Creative Commons reuse license was not verified. Keep the320.6MB source PDF and rendered source-page images as local audit material; do not redistribute the thesis as part of a data release. Link the primary record https://pastel.hal.science/tel-03688021v1 instead. PDF SHA2568c858848ca1a27bcc42e04ca60cfbf146048b53f80b76d7d05ecef459b6ea26a.

**Actual local PDF:** `/Users/deniz2/Documents/ChatGPT/fatigue-ai-research/literature/v3_campaigns/continuation_papers/Merot2021_thesis.pdf`. Its extracted text, exact method excerpts and source-page PNGs are in the same directory.

| Source proof | PDF page / printed page | Local PNG |
|---|---|---|
| Long reference and short alias convention; vertical mechanical specimens |84/60|Merot2021_nomenclature_page84.png|
| Numbered physical build and powder crosswalk; no heat treatment for02/03/04 |85/61,Table2.1|Merot2021_buildtable_page85.png|
| Pretest preparation; F7/F8salt-spray exceptions |111/87|Merot2021_pretest_treatments_page111.png|
| Force control, block protocol and stress definition |115/91|Merot2021_method_page115.png|
| Standard stress versus local peak small-volume stress |280/256,TableG.2|Merot2021_stress_semantics_page280.png|

**Exact build mapping:**02→FS18-019→TLS0993/1/1;03→FS18-020→TLS0993/1/1;04→FS19-006→TLS1051/1/1. `merot_source_specimen_build_crosswalk70.csv` retains each short author alias, exact thesis PMreference, raw plate/position, source build/powder and source page. All70keys match the thesis directly. Surface treatments are conditions, not new production builds. Builds02/03 share a powder lot.

**Verified data files:** `data/external_v3/continuation_papers/merot_first_exposure_unique_physical70_verified.csv`; primary nominal stress43: `merot_first_exposure_air_nominal43.csv`; separate local stress9: `merot_first_exposure_air_localstress9_exploratory.csv`. All rows retain raw author IDs and exact source record indices. The finalizer script reproduces extraction, collision quarantine and final files directly from the raw CSV. See `merot_final_normalization_receipt.json` and `retained_manifest.json`.
