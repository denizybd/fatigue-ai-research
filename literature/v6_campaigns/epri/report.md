# EPRI2020 Rolls-Royce tee: source-backed adjacent strain-life panel

The official EPRI report 3002018273 supplies **14 author-labelled fatigue records**, including **10 at20°C and4 at300°C**, in TableA-18 (PDF143, printedA-31). All14 appear under one Rolls-Royce tee table caption, and the accompanying FigureA-23 associates that tee with HIP and solution annealing after LPBF. The source provides sampleIDs1–14. It does not provide a build-job number, component serial, specimen extraction positions, or per-sample powder certificates. Our component key is a curator identifier for that reported component association, never an invented author build ID.

The AppendixA Rolls-Royce column identifies **powder lot55999**, supplier LSN Diffusion, product F-316LNRR-ALMD, and EOSM280 equipment (TableA-4, PDF120/A-8). AppendixA describes independently manufactured and sectioned/tested components (PDF117/A-5). The sample→tee→Rolls-Royce manufacturer→powder-lot linkage is supported at this component/manufacturer-group level. It is stronger than anonymous condition labels, but weaker than a specimen-by-specimen manufacturing traveler. It must be reported with that distinction. The report labels its material316L/S31603; the powder product string contains316LN. Both are retained without declaring a separate certified alloy identity from the commercial name alone.

The life heading explicitly gives **cycles to failure**, so no factor-of-two conversion is applied. Each numeric record is retained as an author-reported failure. The report does not specify the rupture criterion, runout threshold, complete original test program, or omitted tests. IDs13 and14 have identical numerical coordinates; they remain two source-labelled records, with a duplicate-coordinate flag and no extra claim of independently verified physical specimens.

The reported standard is ASTM E606-19e1, and the table gives total strain amplitude. A full148-page text audit found no further ratio, frequency, waveform, controller setting, prior loading history, or virgin constant-amplitude statement. The E606 reference supports an adjacent strain-life classification; it does not establish the ordinary axial-force HCF protocol. The exact1120°C/2h HIP/solution-treatment schedules in AppendixA.4 name other manufacturers, so those values have not been assigned to the RRtee.

The printed stress and strain-amplitude columns imply an elastic modulus of approximately195.0–195.2GPa at both temperatures. This is a numerical diagnostic consistent with an E×strain pseudo-stress representation; it is not proof of a stated conversion or a source error. Both printed stress columns are retained, and no measured cyclic-stress claim or reconstructed nominal-stress S–N observation is made.

**Admission:**14 exact tabulated adjacent strain-life records with author sample IDs and a component/manufacturer/powder group linkage. **Zero records are admitted to the current model fits or to the RT force-controlled virgin-CA primary panel.** This acquisition does not close the requirement for a second fully qualified RT force-controlled campaign. It does add reproducible public evidence of meaningful source lineage outside that primary domain.

The overlap screen covers all618 FatigueData-AM2022 article metadata records, the13 source-family groups of the current441-row training cohort, and Merot's explicit builds/powder lot. It found no EPRI report/author-family match; two Rolls-Royce corporate-name hits concern Ti-6Al-4V articles and are unrelated alloys. Merot has different explicit FS18 builds and powder lotTLS0993/1/1. This is a bounded source-family screen, not universal proof against unpublished historical reuse. Any future RR316L/316LN fatigue-design-curve derivative must remain in the same conservative source-family block until reuse is checked. A2023 Rolls-Royce design-curve publication is a lead only, not an imported new campaign.

Official download: https://restservice.epri.com/publicdownload/000000003002018273/0/Product

SHA256: `faa725190038019aeb50ed212c0be44fd018ce5c280cb1e1ac3308618d74848a`;24,287,669bytes;148pages; successful HTTP200 public GET on2026-10-20. The source states Copyright2020EPRI, allrightsreserved. Public access is not a CC redistribution license; rawPDF retention is for the local source audit. No author contact, uploads, model fits, or publication occurred.

Reproduce curation from the repository root:

```sh
.venv/bin/python literature/v6_campaigns/epri/curate_epri.py
```

The script verifies the rawPDF hash and all98 numeric cells against a separate regex parser of the retained PDF extraction, then writes the14/10/4-row CSVs, process catalog, evidence ledger, and receipt. Independent primary-reader verification is stored separately under `literature/v6_campaigns/osti_epri2020/independent_source_audit.json` when available.
