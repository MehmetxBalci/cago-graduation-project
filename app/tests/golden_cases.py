"""Fixed request set used to compare the English output of V1.0.0 with V1.1.0 (synthetic fixtures; no real data needed).

`python -m app.tests.golden_cases --write-golden` wrote app/tests/golden_en_v1.json with the V1.0.0 code BEFORE the localization
refactor; test_i18n.py asserts that the English output is still identical. `--equivalence` writes the EN/TR equivalence record
docs/v1_1_i18n_equivalence_evidence.json."""
from __future__ import annotations

import json
from pathlib import Path

from app.adapters import build_app_data
from app.service import AppConfig, generate_recommendations
from app.tests.app_fixtures import CAPS, DATA, REP_TRAIN, VOCAB_DOC

GOLDEN = Path(__file__).with_name("golden_en_v1.json")
SMALL = AppConfig(n_templates=5, candidates_per_template=5)
BASE = {"target_segment": "women", "detail_category": "trousers"}
CASES = [
    ("plain", {}, 0, SMALL),
    ("prefs", {"preferred_dominant_material": "cotton", "breathability": "high", "colour": "black"}, 0, SMALL),
    ("linen_relaxed", {"preferred_dominant_material": "linen", "fit": "relaxed", "breathability": "high"}, 1, SMALL),
    ("stretch_low", {"stretch": "low"}, 3, SMALL),
    ("stretch_low_s4", {"stretch": "low"}, 4, SMALL),
    ("all_functional", {"stretch": "high", "thermal_warmth": "heavy", "breathability": "high", "durability_wear": "reinforced",
                        "moisture_wicking": True, "water_repellent": True, "length_cut": "long", "fit": "slim"}, 2, SMALL),
    ("neutral_warmth", {"thermal_warmth": "standard"}, 0, SMALL),
    ("forbidden_pref", {"preferred_dominant_material": "cotton", "forbidden_materials": ["cotton"]}, 0, SMALL),
    ("forbidden_poly", {"forbidden_materials": ["polyester"]}, 0, SMALL),
    ("conflict_elastane", {"stretch": "high", "forbidden_materials": ["elastane"]}, 0, SMALL),
    ("conflict_wicking", {"moisture_wicking": True, "forbidden_materials": ["polyester", "nylon"]}, 0, SMALL),
    ("conflict_fit_stretch", {"fit": "relaxed", "stretch": "high"}, 0, SMALL),
    ("conflict_elastane_dom", {"preferred_dominant_material": "elastane", "stretch": "none"}, 0, SMALL),
    ("single", {"colour": "black"}, 0, AppConfig(1, 1)),
    ("default_budget", {"breathability": "high"}, 0, AppConfig()),
    ("no_templates", {"target_segment": "men"}, 0, SMALL),
    ("no_candidates", {"target_segment": "men", "detail_category": "shorts", "forbidden_materials": ["cotton"]}, 0, SMALL),
    ("invalid_enum", {"stretch": "medium"}, 0, SMALL),
    ("invalid_breath", {"breathability": "very_high"}, 0, SMALL),
    ("invalid_material", {"preferred_dominant_material": "kryptonite"}, 0, SMALL),
    ("invalid_forbidden", {"forbidden_materials": ["kryptonite", "cotton"]}, 0, SMALL),
    ("removed_fit", {"fit": "skinny"}, 0, SMALL),
    ("removed_length", {"length_cut": "cropped"}, 0, SMALL),
    ("missing_segment", {"target_segment": None}, 0, SMALL),
    ("bad_segment", {"target_segment": "robots"}, 0, SMALL),
    ("bad_category", {"detail_category": "capes"}, 0, SMALL),
    ("unknown_field", {"bogus": 1}, 0, SMALL),
    ("bad_bool", {"water_repellent": "yes"}, 0, SMALL),
    ("bad_colour", {"colour": "   "}, 0, SMALL),
    ("bad_forbidden_type", {"forbidden_materials": "cotton"}, 0, SMALL),
    ("multi_error", {"fit": "skinny", "water_repellent": "yes", "stretch": "medium"}, 0, SMALL),
]
DATA_VARIANTS = {
    "stretch_disabled": lambda: build_app_data(REP_TRAIN, VOCAB_DOC, {"categories": {"trousers": {"controls": {"stretch": False}},
                                                                                     "shorts": {"controls": {}}}}),
    "all_black": lambda: build_app_data(REP_TRAIN.assign(normalized_colour="black"), VOCAB_DOC, CAPS),
}
VARIANT_CASES = [("stretch_disabled", "unavailable_pref", {"stretch": "high"}), ("stretch_disabled", "unavailable_only_pref", {"stretch": "low"}),
                 ("all_black", "black_cell", {"breathability": "high"})]

VOLATILE_STATS = ("seconds_total", "seconds_generation", "seconds_evaluation")


def strip_volatile(result: dict) -> dict:
    out = json.loads(json.dumps(result, default=str))
    for k in VOLATILE_STATS:
        out["stats"].pop(k, None)
    return out


def run_all(**kw) -> dict:
    out = {}
    for name, req, seed, cfg in CASES:
        out[name] = strip_volatile(generate_recommendations({**BASE, **req}, seed=seed, data=DATA, app_cfg=cfg, **kw))
    variants = {k: f() for k, f in DATA_VARIANTS.items()}
    for v, name, req in VARIANT_CASES:
        out[name] = strip_volatile(generate_recommendations({**BASE, **req}, data=variants[v], app_cfg=SMALL, **kw))
    return out


def equivalence_report() -> dict:
    """EN vs TR for every case: identical research outputs (candidate ids, compositions, scores, SR flags, Pareto front,
    roles, digest) and the English text unchanged from V1.0.0."""
    import hashlib
    import platform

    from app.service import research_view
    en, tr = run_all(lang="en"), run_all(lang="tr")
    cases = {}
    for name in en:
        ve, vt = research_view(en[name]), research_view(tr[name])
        blob = lambda v: hashlib.sha256(json.dumps(v, sort_keys=True, default=str).encode()).hexdigest()[:16]  # noqa: E731
        cases[name] = {"status": en[name]["status"], "digest_en": en[name].get("digest"), "digest_tr": tr[name].get("digest"),
                       "research_view_sha256_en": blob(ve), "research_view_sha256_tr": blob(vt), "identical": ve == vt,
                       "candidate_ids": [r["candidate_id"] for r in en[name]["recommendations"]],
                       "roles": [r["roles"] for r in en[name]["recommendations"]],
                       "role_titles_en": [r["role_titles"] for r in en[name]["recommendations"]],
                       "role_titles_tr": [r["role_titles"] for r in tr[name]["recommendations"]],
                       "pareto_front": sorted(p["candidate_id"] for p in en[name]["pareto_points"] if p["is_pareto"]),
                       "first_message_en": en[name]["messages"][0]["text"] if en[name]["messages"] else None,
                       "first_message_tr": tr[name]["messages"][0]["text"] if tr[name]["messages"] else None}
    return {"note": "SYNTHETIC test fixture (app/tests/app_fixtures.py); same request, budget and seed in both languages.",
            "python": platform.python_version(), "n_cases": len(cases), "all_identical": all(c["identical"] for c in cases.values()),
            "cases": cases}


if __name__ == "__main__":
    import sys
    if "--write-golden" in sys.argv:              # only meaningful with the V1.0.0 code (done once before the V1.1.0 refactor)
        GOLDEN.write_text(json.dumps(run_all(), indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {GOLDEN}")
    if "--equivalence" in sys.argv:
        out = Path(__file__).resolve().parents[2] / "docs" / "v1_1_i18n_equivalence_evidence.json"
        rep = equivalence_report()
        out.write_text(json.dumps(rep, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {out}: {rep['n_cases']} cases, all identical: {rep['all_identical']}")
