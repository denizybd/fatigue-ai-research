# Merot initial-block source recovery

The broad paper search initially admitted no new data. A subsequently authorized, separately frozen first-exposure extension recovered a useful physical cohort from the producer's CC BY4.0 Zenodo dataset6653187 and the primary306-page thesis tel-03688021v1. No model was fitted in this source work.

The raw dataset has262loading-block rows for103short author aliases.105rows are marked Step0 because K2 has three such rows. The raw CSV explicitly supplies plate number and specimen number. The thesis defines PM-[plate]-[type][specimen] plus the short letter/digit alias on PDF84, and maps numbered physical builds on PDF85/Table2.1:

| Raw plate | Thesis number | Actual production build | Powder batch |
|---|---|---|---|
|2|02|FS18-019|TLS0993/1/1|
|3|03|FS18-020|TLS0993/1/1|
|4|04|FS19-006|TLS1051/1/1|

These are three physical builds in one author research program. Surface-treatment categories are separate conditions, not extra production batches. All builds use Farsoon FS271M, nitrogen, vertical mechanical specimens,225W,1000mm/s,hatch90µm,layer30µm. Powder was not recycled between these builds. Powder batches02/03 are shared even though the production builds differ.

The initial-block eligibility was frozen before extraction. One first recorded exposure is kept per unique author specimen and unique physical plate/position. A failure in the first block is an event; surviving the first stop is right-censoring at recorded N. No later stress block, accumulated life, Miner/Basquin/Maxwell-Nicholas equivalent life, or fracture-derived defect feature enters the verified tables.

Quarantine is necessary. Ten physical keys are shared by21author aliases; these include D0/K2 and a three-alias key D8/F2/J4. Twelve aliases have incomplete raw plate/position metadata. All colliding aliases were detected before dropping K2, so D0 is excluded too. K2's extra Step0rows are also quarantined. This leaves70unique physical initial-exposure records. All70raw physical keys were independently matched to exact full PMreferences in thesis tables/text. Some collisions are repeated in the thesis, whereas C9has an explicit CSV/thesis plate contradiction (CSV03/F43 versus thesis02/F43); these remain excluded.

Of the70verified records,52were tested in air at20°C and18in salt spray at35°C. Air methods on PDF114–115 specify uniaxial force control, frequency1/15/20/25Hz as appropriate, and stepped tests with1e6cycles per ordinary block. Salt-spray methods on PDF116–117 use the same loading method and include1e7block stops. Each retained first block is constant amplitude. The distinction from the eventual stepped experiment is explicit.

The52air records need a stress-basis split. Standard geometry uses nominal macroscopic gauge stress (thesisG.1/G.2 show σnom=σmax, Ktapproximately1), yielding **43primary nominal-stress records:17failures and26right-censors**. Nine small-volume specimens use specimen-specific local peak stress σmax=Kt·σnom. Their exact Ktvalues are not supplied in the raw dataset; only rounded later-stage nominal/peak values occur inG.2. Those nine remain a separate exploratory local-stress cohort, with6failures and3censors. No exact stress conversion was invented from rounded later-stage tables.

The43primary rows span three builds but some build×surface conditions are small. The build02reference(n10), build02pre-corroded(n12), and build03pre-corroded(n9) conditions support acquisition pilots with at least6records. Small-volume build03(n9) must not be silently mixed into a nominal-stress transfer analysis. The remaining standard-geometry conditions are retained but small. Pre-corroded preparation is heterogeneous; F8was prepared by85days of salt spray, while most other pre-corroded air specimens used electrochemical exposure. This is recorded as a source condition, not fitted away.

This is a retrospective source recovery. Outcomes were historically available; it is not fresh outcome-blind confirmation. All Merot106552, Merot108883 and Auffray109107 family rows must be excluded from population training. Later reuse in Auffray does not create an independent author campaign.

Files: verified70, primary air nominal43, separate local-stress9, all105raw Step0audit candidates,35quarantined Step0rows, exact specimen/build crosswalk70, frozen eligibility, method excerpts, PDF visual receipts, raw producer metadata and retained hashes.
