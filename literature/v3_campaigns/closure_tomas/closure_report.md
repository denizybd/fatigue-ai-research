# Tomaszewski source-closure pass

**No additional specimen→physical build join was recovered. SS_A02W_01..09 remain inadmissible for the identity-qualified primary benchmark.**

The producer workbook was inspected as both an Excel document and the complete XLSX ZIPpackage. It contains one visible worksheet, no hidden sheet/rows/columns, comments, cell hyperlinks, defined names, table objects, custom properties, external links or embedded files. Core properties have no author/subject/description/identifier evidence; the application metadata has one sheet and an empty company. ZIPrelationships only point to ordinary workbook/style/theme/shared-string parts. XMLURLs are schema namespaces, not external manufacturing records. The full artifact inventory, text cells and relationships are retained in `workbook_full_artifact_audit.json`.

The freshly fetched official Zenodo7650061 metadata still describes a **compilation** of stress-controlled HCF data. It supplies the author, project and CC BY4.0license but no actual production build, plate, specimen position, manufacturing date or article DOI relation. The workbook explicitly defines W/L as building along specimen width/length; they are orientation labels, not batch IDs.

The2023author manuscript (10.1016/j.ijfatigue.2022.107378) genuinely states that its specimens came from one build plate (PDF6and7). Table2onPDF8has fatigue group counts A02=9,A08=9,A32=10. The raw standard-width/R=-1/zero-working-length rows instead number9,13,15. The nine A02Wrows match the A02geometry/count and the paper's width-direction diagram, but neither manuscript nor workbook names those raw author IDs as members of the paper plate. A02/A08/A32 are geometry-class labels in the paper. A matching subset count cannot supply the missing physical join.

The2024official manuscript (10.1016/j.ijfatigue.2024.108225) supplies length-group labels L00/L05/L20/L50, individualLxx_nn outcomes and shared manufacturing settings. It does not identify SS_A02W_01..09or tie them to a single physical build. A plate photo and constant process settings are not a physical-run identifier. No exact A02Wauthor ID appears in either article.

Additional unresolved metadata agree with keeping the candidate separate: workbook10Hz versus related manuscripts20Hz, and “laboratory conditions” rather than numeric room temperature. The workbook's macrocrack endpoint is compatible with the manuscripts' continuous-crack criterion, but compatibility does not establish row identity.

Concrete missing source: an existing author-produced inventory naming the raw IDs and physical plate, or an explicit raw-dataset scope statement tying them to the one-plate article campaign. Neither was found in the complete public artifact metadata. No correspondence or model fitting was performed. Source files were not modified; the workbook SHA256remains30a45bb604d1b13f38f6e36047174fbcc2734f38019c683ba5dd149e1d4f4b35and its MD5matches the producer record.

Evidence: `closure_verdict.json`, `source_closure_evidence.json`, `A02W9_source_rows_readonly.csv`, refreshed Zenodo metadata and visual PDFreceipts.
