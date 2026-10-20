"""Finalize independently audited first recorded exposure; no model fitting."""
from pathlib import Path
import csv
import collections
import hashlib
import json
import math
import re

ROOT = Path(__file__).resolve().parents[3]
LIT = Path(__file__).resolve().parent
DATA = ROOT / "data/external_v3/continuation_papers"
BUILD = {"2": ("02", "FS18-019", "TLS 0993/1/1"),
         "3": ("03", "FS18-020", "TLS 0993/1/1"),
         "4": ("04", "FS19-006", "TLS 1051/1/1")}


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def extract_candidates():
    raw_path = DATA / "data_fatigue_merot.csv"
    digest = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    raw = list(csv.DictReader(raw_path.open(encoding="utf-8-sig")))
    assert raw.pop(0)["Sample"] == "-", "Expected the producer's units row"
    aliases = collections.defaultdict(list)
    physical = collections.defaultdict(set)
    for index, row in enumerate(raw, 1):
        row["source_data_record_index"] = str(index)
        aliases[row["Sample"]].append(row)
        if row["Numéro plateau"] and row["Numéro eprouvette"]:
            physical[(row["Numéro plateau"], row["Numéro eprouvette"])].add(row["Sample"])
    collided = {key for key, names in physical.items() if len(names) > 1}
    candidates = []
    for row in raw:
        if row["Step"] != "0":
            continue
        alias, plate, specimen = row["Sample"], row["Numéro plateau"], row["Numéro eprouvette"]
        reasons = []
        if not plate or not specimen:
            reasons.append("incomplete_source_plate_or_specimen_coordinates")
        if (plate, specimen) in collided:
            reasons.append("physical_key_shared_across_author_aliases")
        if sum(item["Step"] == "0" for item in aliases[alias]) != 1:
            reasons.append("multiple_Step0_rows_for_author_alias")
        if min(float(item["Step"]) for item in aliases[alias]) != 0:
            reasons.append("nonzero_prior_step")
        amplitude, maximum, ratio = map(float, (row["s_amp"], row["s_max"], row["R"]))
        assert math.isclose(amplitude, maximum * (1 - ratio) / 2, rel_tol=1e-12)
        event = {"oui": "1", "non": "0"}[row["Fracture"]]
        environment = "air" if row["Batch"].endswith(" air") else "salt_spray_BS" if row["Batch"].endswith(" BS") else "unspecified"
        candidates.append({**row, "source_doi": "10.5281/zenodo.6653187",
            "article_doi": "10.1016/j.ijfatigue.2021.106552", "source_sha256": digest,
            "source_specimen_id": alias, "source_plate_id": plate,
            "source_specimen_number_on_plate": specimen,
            "source_physical_key": f"{plate}:{specimen}" if plate and specimen else "",
            "canonical_physical_key": f"merot_zenodo6653187:plate={plate}:specimen={specimen}" if plate and specimen else "",
            "treatment_batch_raw": row["Batch"], "environment": environment,
            "temperature_C": row["Temp"], "sigma_a_MPa": row["s_amp"], "sigma_max_MPa": row["s_max"],
            "stress_ratio_R": row["R"], "frequency_Hz": row["f"], "cycles_first_block": row["N"],
            "log10_cycles_first_block": str(math.log10(float(row["N"]))), "event": event,
            "endpoint_type": "failure_at_initial_block" if event == "1" else "right_censored_at_initial_block_stop",
            "first_step_candidate_eligible": str(not reasons).lower(), "exclusion_reasons": ";".join(reasons),
            "physical_plate_semantics_verified": "false", "primary_axial_control_mode_verified": "false",
            "population_training_exclusion_family": "Merot2021_106552;Merot2022_108883;Auffray2025_109107",
            "confirmation_status": "retrospective_source_recovery_not_outcome_blind"})
    assert len(candidates) == 105
    write_csv(DATA / "merot_all_Step0_candidates105.csv", candidates)
    write_csv(DATA / "merot_first_exposure_unique_physical70_pending_methods.csv",
              [row for row in candidates if row["first_step_candidate_eligible"] == "true"])
    write_csv(DATA / "merot_first_exposure_quarantine35.csv",
              [row for row in candidates if row["first_step_candidate_eligible"] == "false"])
    return candidates


def main():
    text = (LIT / "Merot2021_thesis.txt").read_text()
    refs = collections.defaultdict(list)
    for page in re.split(r"=== PDF_PAGE ", text)[1:]:
        number = page.split(" ===", 1)[0]
        for match in re.finditer(r"(PM-(\d+)-F(\d+))\s+([A-Z]\d+)\b", page):
            refs[match[4]].append((match[1], str(int(match[2])), str(int(match[3])), number))
    candidates = extract_candidates()
    eligible = []
    crosswalk = []
    for row in candidates:
        if row["first_step_candidate_eligible"] != "true":
            continue
        alias, plate, specimen = row["Sample"], row["source_plate_id"], row["source_specimen_number_on_plate"]
        exact = [ref for ref in refs[alias] if ref[1:3] == (plate, specimen)]
        assert exact, (alias, plate, specimen, refs[alias])
        longref, _, _, source_page = exact[0]
        thesis_plate, build, powder = BUILD[plate]
        # Preserve only pretest identifiers, prescribed conditions and first block
        # outcomes. The source's defect fractography and equivalent-life columns
        # remain in the raw audit file and cannot become model inputs here.
        keep = ["Sample", "Step", "source_data_record_index", "source_doi", "article_doi",
                "source_sha256", "source_specimen_id", "source_plate_id",
                "source_specimen_number_on_plate", "source_physical_key", "canonical_physical_key",
                "treatment_batch_raw", "environment", "temperature_C", "sigma_a_MPa", "sigma_max_MPa",
                "stress_ratio_R", "frequency_Hz", "cycles_first_block", "log10_cycles_first_block",
                "event", "endpoint_type", "first_step_candidate_eligible", "exclusion_reasons",
                "physical_plate_semantics_verified", "primary_axial_control_mode_verified",
                "population_training_exclusion_family", "confirmation_status"]
        result = {field: row[field] for field in keep}
        result.update(source_full_specimen_reference=longref, source_thesis_plate_number=thesis_plate,
                      source_build_id=build, source_powder_batch_id=powder,
                      source_thesis_id="tel-03688021v1", source_thesis_pdf_page=source_page,
                      build_mapping_evidence="Merot2021 thesis PDF84-85; Table2.1; naming convention printed60",
                      material="SS316L", process="LPBF", machine="Farsoon FS271M",
                      build_orientation="vertical; loading direction parallel to build direction",
                      heat_treatment="none for source builds02/03/04; machining/polishing allowed",
                      control_mode="uniaxial force control", method_evidence="Merot2021 thesis PDF114-117",
                      physical_plate_semantics_verified="true", primary_axial_control_mode_verified="true")
        small = row["treatment_batch_raw"] == "Petit volume air"
        result["stress_definition"] = ("local_peak_gauge_stress_Kt_adjusted" if small
                                       else "nominal_macroscopic_gauge_stress_Kt_approximately1")
        result["stress_definition_evidence"] = "Merot2021 thesis PDF115; TablesG.1/G.2 PDF279-280"
        result["primary_nominal_stress_eligible"] = str(not small and row["environment"] == "air").lower()
        result["precorrosion_method_note"] = ("salt spray85days; thesis PDF111" if alias == "F8" else
                                              "mixed prescribed electrochemical exposures; see thesis TableF.1" if row["treatment_batch_raw"] == "Corrodé air" else
                                              "not applicable or see source treatment group")
        eligible.append(result)
        crosswalk.append({key: result[key] for key in ["Sample", "source_full_specimen_reference",
                         "source_plate_id", "source_specimen_number_on_plate", "source_build_id",
                         "source_powder_batch_id", "source_thesis_pdf_page"]})
    assert len(eligible) == 70
    assert len({row["canonical_physical_key"] for row in eligible}) == 70
    air = [row for row in eligible if row["environment"] == "air"]
    nominal = [row for row in eligible if row["primary_nominal_stress_eligible"] == "true"]
    small = [row for row in air if row["stress_definition"] == "local_peak_gauge_stress_Kt_adjusted"]
    assert (len(air), len(nominal), len(small)) == (52, 43, 9)
    write_csv(DATA / "merot_first_exposure_unique_physical70_verified.csv", eligible)
    write_csv(DATA / "merot_first_exposure_air_nominal43.csv", nominal)
    write_csv(DATA / "merot_first_exposure_air_localstress9_exploratory.csv", small)
    write_csv(LIT / "merot_source_specimen_build_crosswalk70.csv", crosswalk)
    receipt = {"rows": 70, "air_rows": 52, "air_nominal_stress_primary_rows": 43,
               "air_local_peak_stress_exploratory_rows": 9, "salt_spray_separate_rows": 18,
               "primary_builds": sorted({row["source_build_id"] for row in nominal}),
               "all70_reference_crosschecks": "Exact author long reference matches thesis for every eligible raw plate/specimen key.",
               "air_events": dict(collections.Counter(row["event"] for row in air)),
               "nominal43_events": dict(collections.Counter(row["event"] for row in nominal)),
               "local9_events": dict(collections.Counter(row["event"] for row in small)),
               "collision_policy": "Physical keys collided across ANY raw author aliases are excluded, including D0 via K2.",
               "stress_policy": "No Kt conversion invented. Nine local-stress small-volume specimens are separately marked and excluded from primary nominal-stress panel.",
               "population_family_exclusion": ["10.1016/j.ijfatigue.2021.106552", "10.1016/j.engfracmech.2022.108883", "10.1016/j.ijfatigue.2025.109107"],
               "leakage_policy": "No later step, equivalent-life correction, final fracture stress or postfailure defect measurement retained in final eligible tables.",
               "validation_status": "Retrospective recovery; no outcome-blind confirmation; no models fitted here."}
    (LIT / "merot_final_normalization_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
