"""V1.1.0 localization tests (English / Turkish). Presentation only: the research outputs must be identical in both languages.

Covers: catalog completeness and placeholders, strict lookup, vocabulary coverage against the (read-only) source vocabulary
files, reversible display <-> internal mappings, EN/TR equivalence of the research outputs for the same request and seed,
English wording unchanged from V1.0.0 (golden file), Turkish explanations / warnings / empty states, Streamlit language
switching (state preserved, no regeneration) and frozen-source / manifest integrity.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
from pathlib import Path

import pytest

from app.adapters import REASON_CODES, REQUIRED_FILES, UI_LABELS, UI_TO_REQUEST, field_availability
from app.i18n import EN, SUPPORTED_LANGUAGES, TranslationError, Translator, get_translator
from app.i18n import en as en_cat
from app.i18n import tr as tr_cat
from app.i18n.translator import VOCAB_DOMAINS, colour_fully_translated, placeholders, translate_colour
from app.presenters import (PREFERENCE_IDS, ROLE_ORDER, SR_ORDER, change_sentence, contains_banned_claim, disclaimer, evidence_phrase,
                            preference_sentence, rule_change_sentence, sorting_summary_text, sr_status, trade_off_sentence)
from app.service import (STATUS_INVALID, STATUS_NO_CANDIDATES, STATUS_NO_TEMPLATES, STATUS_OK, AppConfig, generate_recommendations,
                         localize_result, research_view)
from app.tests.app_fixtures import CAPS, DATA, REP_ALL, VOCAB_DOC
from app.tests.golden_cases import CASES, GOLDEN, run_all
from cago.requirements.properties import TEXT_PATTERNS
from cago.requirements.schema import ENUMS

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
TR = Translator("tr", strict=True)
ENS = Translator("en", strict=True)
SMALL = AppConfig(n_templates=5, candidates_per_template=5)
BASE = {"target_segment": "women", "detail_category": "trousers"}


def run(req=None, lang="en", seed=0, cfg=SMALL, data=DATA):
    return generate_recommendations({**BASE, **(req or {})}, seed=seed, data=data, app_cfg=cfg, lang=lang)


def visible_texts(result) -> list[str]:
    """Every user-facing string of a service result (technical evidence = frozen engine output, excluded)."""
    out = [m["text"] for m in result["messages"]] + [result["config_note"]]
    for rec in result["recommendations"]:
        out += rec["role_titles"] + [rec["category"], rec["sorting_summary"], rec["intent_label"], rec["plausibility_label"]]
        for k in ("headline", "role_reasons", "comparisons", "changes_from_template", "confirmed_rule_changes", "trade_offs_vs_template"):
            out += rec[k]
        out += [x for p in rec["preferences"] for x in (p["preference"], str(p["requested"]), p["status"], p["explanation"])]
        out += [x for s in rec["sr"] for x in (s["name"], s["status"], s["detail"])]
        out += [x for c in rec["composition"] for x in (c["component"], c["text"])]
    out += [r for p in result["pareto_points"] for r in p["roles"]]
    return out


# ================================================================ catalogs
def test_catalogs_have_identical_keys():
    assert set(en_cat.MESSAGES) == set(tr_cat.MESSAGES), {"missing_in_tr": sorted(set(en_cat.MESSAGES) - set(tr_cat.MESSAGES)),
                                                          "extra_in_tr": sorted(set(tr_cat.MESSAGES) - set(en_cat.MESSAGES))}


def test_no_empty_or_untranslated_turkish_strings():
    assert all(isinstance(v, str) and v.strip() for v in en_cat.MESSAGES.values())
    assert all(isinstance(v, str) and v.strip() for v in tr_cat.MESSAGES.values())
    # Turkish strings identical to English are only allowed for format-only / identifier-only entries ("demo" is also Turkish)
    same = {k for k in en_cat.MESSAGES if en_cat.MESSAGES[k] == tr_cat.MESSAGES[k]}
    allowed = {k for k in same if not re.search(r"[A-Za-z]{3,}", re.sub(r"\{[a-z_]+\}|SR[1-5]|CAGO|TRAIN|TEST|JSON|Parquet|demo", "", en_cat.MESSAGES[k]))}
    assert same == allowed, sorted(same - allowed)


def test_placeholders_match_between_languages():
    bad = {k: (placeholders(en_cat.MESSAGES[k]), placeholders(tr_cat.MESSAGES[k])) for k in en_cat.MESSAGES
           if placeholders(en_cat.MESSAGES[k]) != placeholders(tr_cat.MESSAGES[k])}
    assert bad == {}


def test_every_static_key_used_in_the_app_exists():
    used: set[str] = set()
    for p in (ROOT / "app").rglob("*.py"):
        if "tests" in p.parts or "i18n" in p.parts:
            continue
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "t" and node.args and isinstance(node.args[0], ast.Constant):
                used.add(node.args[0].value)
    assert used and used <= set(en_cat.MESSAGES), sorted(used - set(en_cat.MESSAGES))


def test_dynamic_key_families_are_complete():
    keys = set(en_cat.MESSAGES)
    fam = [f"role.{r}" for r in ROLE_ORDER] + [f"sr.{r}.{s}" for r in SR_ORDER for s in ("name", "ok", "name_lc")]
    fam += [f"field.{f}" for f in UI_LABELS] + [f"field_lc.{f}" for f in UI_LABELS] + [f"pref.{p}" for p in PREFERENCE_IDS]
    fam += [f"pstatus.{s}" for s in ("satisfied", "partially_satisfied", "not_satisfied", "not_scored")]
    fam += [f"availability.{c}" for c in REASON_CODES.values()] + [f"data.file.{n}" for n in REQUIRED_FILES]
    fam += [f"disclaimer.{i}" for i in range(1, 6)] + [f"bucket.{b}" for b in ("none", "low", "high", "out_of_range")]
    fam += [f"data.problem.{c}" for c in ("unreadable_parquet", "missing_columns", "train_rows_unreadable", "no_train_rows", "unreadable_json",
                                         "missing_keys", "missing_categories")]
    assert set(fam) <= keys, sorted(set(fam) - keys)
    assert all(UI_TO_REQUEST.get(f) is not None for f in UI_LABELS)


def test_english_field_labels_equal_v1_labels():
    assert {f: ENS.field(f) for f in UI_LABELS} == UI_LABELS
    assert all(ENS.field_lc(f) == UI_LABELS[f].lower() for f in UI_LABELS)


# ================================================================ translator mechanics
def test_lookup_interpolation_and_missing_keys():
    assert TR.t("status.hard_valid", n=12) == "12 aday zorunlu kısıtları sağlıyor"
    with pytest.raises(TranslationError):
        TR.t("status.hard_valid")                                     # placeholder without value is never rendered as "{n}"
    with pytest.raises(TranslationError):
        TR.t("no.such.key")
    lenient = Translator("tr", strict=False)
    lenient.messages = {k: v for k, v in tr_cat.MESSAGES.items() if k != "form.generate"}
    assert lenient.t("form.generate") == "Generate recommendations" and lenient.missing == {"form.generate"}   # recorded, not silent
    strict = Translator("tr", strict=True)
    strict.messages = lenient.messages
    with pytest.raises(TranslationError):
        strict.t("form.generate")
    with pytest.raises(ValueError):
        Translator("de")
    assert get_translator("tr") is get_translator("tr") and SUPPORTED_LANGUAGES == ("en", "tr")


def test_number_formatting():
    assert (ENS.pct(95), ENS.pct(2.5), TR.pct(95), TR.pct(2.5)) == ("95%", "2.5%", "%95", "%2,5")
    assert TR.num(0.6012, ".3f") == "0,601" and ENS.num(0.6012, ".3f") == "0.601"
    assert TR.pct_token("3.5%") == "%3,5" and TR.pct_token("abc") == "abc"


# ================================================================ vocabulary: display <-> internal
def _source_vocab():
    return json.loads((PROCESSED / "ml_material_vocabulary.json").read_text(encoding="utf-8"))


def _source_categories():
    return sorted(json.loads((PROCESSED / "category_capabilities.json").read_text(encoding="utf-8"))["categories"])


def test_turkish_vocabulary_covers_source_vocabularies():
    v = _source_vocab()
    physical = [t for t in v["tokens"] if t not in v["special_tokens"]]
    domains = {"material": physical + sorted(v["canonical_to_token"]), "category": _source_categories(),
               "segment": ["women", "men", "kids", "baby"], "component": v["component_names"],
               "component_class": [c.replace("_component", "") for c in v["component_classes"]], "text_tag": sorted(TEXT_PATTERNS),
               **{f: list(vals) for f, vals in ENUMS.items()}}
    missing = {d: [x for x in vals if not TR.is_translated(d, x)] for d, vals in domains.items()}
    assert {d: m for d, m in missing.items() if m} == {}
    assert set(VOCAB_DOMAINS) >= set(domains)


def test_identifiers_shown_unchanged_are_deliberate():
    for domain, labels in tr_cat.VOCAB.items():
        same = {k for k, lab in labels.items() if lab == k}
        assert same <= tr_cat.RETAINED.get(domain, set()), (domain, sorted(same - tr_cat.RETAINED.get(domain, set())))


def test_required_examples_map_both_ways():
    mats, fits = ["cotton", "linen", "polyester"], list(ENUMS["fit"])
    assert TR.to_internal("material", "Pamuk", mats) == "cotton" and TR.to_internal("material", "Keten", mats) == "linen"
    assert TR.to_internal("colour", "Siyah", ["black", "white"]) == "black"
    assert TR.to_internal("fit", "Rahat kesim", fits) == "relaxed"
    assert TR.option_labels("material", mats)["cotton"] == "Pamuk" and TR.label("material", "cotton") == "pamuk"
    assert ENS.option_labels("material", mats) == {m: m for m in mats}                     # English shows the identifiers (V1)


@pytest.mark.parametrize("domain", ["segment", "category", "material", "fit", "length_cut", "stretch", "thermal_warmth", "breathability",
                                    "durability_wear", "colour"])
@pytest.mark.parametrize("lang", ["en", "tr"])
def test_option_mapping_is_unique_and_reversible(domain, lang):
    t = Translator(lang, strict=True)
    if domain == "material":
        values = list(_source_vocab()["canonical_to_token"]) + [x for x in _source_vocab()["tokens"] if x not in ("PAD", "OTHER")]
    elif domain == "category":
        values = _source_categories()
    elif domain == "segment":
        values = ["women", "men", "kids", "baby"]
    elif domain == "colour":
        values = sorted(_recorded_colours() | {"grey", "gray", "black", "navy", "navy blue"})
    else:
        values = list(ENUMS[domain])
    labels = t.option_labels(domain, values)
    assert len(set(labels.values())) == len(labels)
    assert all(t.to_internal(domain, lab, values) == v for v, lab in labels.items())


def _recorded_colours() -> set[str]:
    """Colours that occur in recorded (frozen) results; read-only."""
    found: set[str] = set()
    for p in list(PROCESSED.glob("*.json")) + [ROOT / "docs" / "v1_demo_evidence.json"]:
        s = p.read_text(encoding="utf-8")
        found |= set(re.findall(r'"(?:normalized_colour|colour|candidate_colour)"\s*:\s*"([^"]+)"', s))
        found |= {m.strip() for m in re.findall(r"colour=([a-z /\-]+)", s)}
    return {c for c in found if c and len(c) < 60}


def test_colour_translation_policy():
    assert translate_colour("black") == "siyah" and translate_colour("navy blue") == "lacivert"
    assert translate_colour("light beige/leopard print") == "açık bej/leopar desenli"
    assert translate_colour("black/spider-man") == "siyah/spider-man"                  # licence names kept as in the data
    assert translate_colour("mole") == "mole" and not colour_fully_translated("mole")
    basic = [c for c in _recorded_colours() if all(w in tr_cat.COLOUR_WORDS for w in re.split(r"[ /]", c.replace(" - ", " ")) if w)]
    assert basic and all(colour_fully_translated(c) for c in basic)
    assert ENS.label("colour", "light beige/leopard print") == "light beige/leopard print"


# ================================================================ EN / TR equivalence of research outputs
@pytest.mark.parametrize("name,req,seed,cfg", CASES, ids=[c[0] for c in CASES])
def test_identical_research_outputs_in_both_languages(name, req, seed, cfg):
    en_r = run(req, "en", seed, cfg)
    tr_r = run(req, "tr", seed, cfg)
    assert research_view(en_r) == research_view(tr_r)
    assert en_r.get("digest") == tr_r.get("digest")
    assert [r["candidate_id"] for r in en_r["recommendations"]] == [r["candidate_id"] for r in tr_r["recommendations"]]
    assert [r["roles"] for r in en_r["recommendations"]] == [r["roles"] for r in tr_r["recommendations"]]
    # re-rendering a stored result gives exactly the directly generated texts, in both directions
    strip = lambda r: {k: v for k, v in json.loads(json.dumps(r, default=str)).items() if k != "stats"}  # noqa: E731
    assert strip(localize_result(en_r, "tr")) == strip(tr_r)
    assert strip(localize_result(tr_r, "en")) == strip(en_r)


def test_research_engine_receives_identical_requests(monkeypatch):
    import app.service as svc
    seen = []
    real_gen, real_eval = svc.generate_sorting_aware, svc.evaluate_and_select
    monkeypatch.setattr(svc, "generate_sorting_aware", lambda req, *a, **k: seen.append(("gen", json.dumps(req, sort_keys=True, default=str),
                                                                                         repr(a[-1]))) or real_gen(req, *a, **k))
    monkeypatch.setattr(svc, "evaluate_and_select", lambda req, *a, **k: seen.append(("eval", json.dumps(req, sort_keys=True, default=str)))
                        or real_eval(req, *a, **k))
    form = {"segment": "women", "category": "trousers", "preferred_material": "linen", "fit": "relaxed", "forbidden_materials": ["polyester"],
            "breathability": "high", "moisture_wicking": True}
    for lang in ("en", "tr"):
        generate_recommendations(form, data=DATA, app_cfg=SMALL, is_form=True, lang=lang)
    half = len(seen) // 2
    assert seen[:half] == seen[half:] and half == 2
    assert "Keten" not in seen[0][1] and "Pamuk" not in seen[0][1] and '"linen"' in seen[0][1]


def test_localize_result_never_regenerates_or_mutates(monkeypatch):
    import app.service as svc
    r = run({"breathability": "high", "preferred_dominant_material": "linen"})
    before = copy.deepcopy(r)
    monkeypatch.setattr(svc, "generate_sorting_aware", lambda *a, **k: pytest.fail("generator called"))
    monkeypatch.setattr(svc, "evaluate_and_select", lambda *a, **k: pytest.fail("evaluation called"))
    tr_view = localize_result(r, "tr")
    assert r == before                                                    # stored result untouched
    assert tr_view["lang"] == "tr" and research_view(tr_view) == research_view(r)


def test_duplicate_role_deduplication_is_language_independent():
    for lang in ("en", "tr"):
        r = run({"colour": "black"}, lang, cfg=AppConfig(1, 1))
        assert len(r["recommendations"]) == 1 and r["recommendations"][0]["roles"] == ["balanced", "sorting_focused", "intent_focused"]
    assert run({"colour": "black"}, "tr", cfg=AppConfig(1, 1))["recommendations"][0]["role_titles"] == ["Dengeli", "Ayıklama Odaklı", "Tercih Odaklı"]


# ================================================================ English unchanged from V1.0.0
def test_english_output_identical_to_v1_golden():
    """app/tests/golden_en_v1.json was written by the V1.0.0 code before the localization refactor."""
    gold = json.loads(GOLDEN.read_text(encoding="utf-8"))
    now = json.loads(json.dumps(run_all(), default=str))

    def subset(g, n):                        # V1.1.0 may ADD keys (render_data, ids); every V1 value must be unchanged
        if isinstance(g, dict):
            return isinstance(n, dict) and all(k in n and subset(v, n[k]) for k, v in g.items())
        if isinstance(g, list):
            return isinstance(n, list) and len(g) == len(n) and all(subset(a, b) for a, b in zip(g, n))
        return g == n
    bad = [k for k in gold if not subset(gold[k], now[k])]
    assert bad == []


# ================================================================ Turkish wording
def test_turkish_texts_contain_no_leftover_english():
    english = re.compile(r"\b(the|and|with|from|template|candidate|violations?|preferences?|not|is|are|of|for|to|change|compared|"
                         r"trade-off|scored|satisfied|material|colour|composition|stretch|fabric|fibres?|lining|shell|main)\b", re.I)
    res = run_all(lang="tr")
    hits = {(m.group(0), t) for r in res.values() for t in visible_texts(r) for m in english.finditer(t)}
    hits = {h for h in hits if h[0].lower() != "in"}                     # Turkish suffix after %5'in
    assert hits == set()
    assert all(not contains_banned_claim(" ".join(visible_texts(r))) for r in res.values())


def test_turkish_explanations_and_warnings():
    r = run({"stretch": "high", "forbidden_materials": ["elastane"]}, "tr")
    w = next(m for m in r["messages"] if m["code"] == "preference_conflict")
    assert "elastan yasaklandı" in w["text"] and "Olası tercih çatışması" in w["text"]
    r = run({"preferred_dominant_material": "cotton", "forbidden_materials": ["cotton"]}, "tr")
    assert any("zorunlu bir kısıttır" in m["text"] for m in r["messages"])
    r = run({}, "tr")
    assert any(m["text"] == "Hiç esnek tercih belirtilmedi; bu nedenle Tercih Odaklı öneri yok." for m in r["messages"])
    r = run({"thermal_warmth": "standard"}, "tr")
    msg = next(m["text"] for m in r["messages"] if m["code"] == "no_intent")
    assert "sıcak tutma" in msg and "nötrdür" in msg
    r = run({"breathability": "high", "preferred_dominant_material": "linen", "fit": "relaxed"}, "tr", seed=1)
    rec = r["recommendations"][0]
    assert rec["role_titles"][0] == "Dengeli" and "Tercihlere Uyum" in " ".join(rec["role_reasons"] + rec["comparisons"])
    assert all(p["explanation"] and p["technical"] for p in rec["preferences"])
    assert any("Bileşime dayalı tahmin" in p["explanation"] for p in rec["preferences"])
    assert all(c.startswith("Değişiklik ") for c in rec["changes_from_template"])
    assert [s["rule"] for s in rec["sr"]] == list(SR_ORDER)                         # SR identifiers never translated


def test_turkish_sr_wording_keeps_the_disclaimer():
    o = {f"sr{i}_violation": False for i in range(1, 6)}
    assert sorting_summary_text(0, sr_status(o, "red", TR), TR) == "CAGO SR1–SR5 ayıklama tarama kurallarına göre ihlal tespit edilmedi."
    t = sorting_summary_text(1, sr_status({**o, "sr4_violation": True}, "black", TR), TR)
    assert t.startswith("5 ayıklama tarama kuralından 1") and "SR4" in t
    assert any("geri dönüştürülebilirliği veya üretilebilirliği garanti etmez" in d for d in disclaimer(TR))
    assert not contains_banned_claim(" ".join(disclaimer(TR)))
    assert "siyah" in sr_status({**o, "sr4_violation": True}, "black", TR)[3]["detail"]


def test_turkish_presenter_sentences():
    p = {"preference": "breathability", "requested_value": "high", "scorable": True, "satisfaction_0_1": 1.0,
         "evidence": ["breathable_fibre_share=1.00"], "unscorable_reason": None}
    s = preference_sentence(p, TR)
    assert "'Yüksek' nefes alabilirlik isteğini tam olarak karşılıyor" in s and "%100" in s and "ölçülmüş bir özellik değil" in s
    p = {"preference": "fit", "requested_value": "slim", "scorable": False, "satisfaction_0_1": None, "evidence": [],
         "unscorable_reason": "no_label_evidence"}
    assert "karşılanmamış sayılmaz" in preference_sentence(p, TR)
    p = {"preference": "preferred_dominant_material", "requested_value": "linen", "scorable": True, "satisfaction_0_1": 0.0,
         "evidence": ["primary_component=shell", "dominant=cotton=60%"], "unscorable_reason": None}
    assert preference_sentence(p, TR) == "En büyük paya sahip malzeme (ana kumaş: dış kumaş): pamuk, %60; istenen malzeme (keten) değil."
    assert evidence_phrase("text:membrane,quick_dry", TR) == "ürün metninde geçen ifadeler: membran, hızlı kuruyan"
    sub = {"step": 0, "type": "substitution", "reason": "forbidden_repair", "component_name": "shell", "from_material": "elastane",
           "to_material": "cotton", "pct": 3.0}
    assert change_sentence(sub, TR) == ("Değişiklik 1: dış kumaş bileşeni içinde elastan yerine pamuk kullanıldı (bu malzeme bileşenin %3 "
                                        "kadarını oluşturuyordu) — yasaklı bir malzemeyi çıkarmak için.")
    mv = {"step": 1, "type": "percentage", "component_name": "shell", "from_material": "polyester", "to_material": "cotton", "delta": 1.5,
          "pct_before": [40.0, 60.0], "pct_after": [38.5, 61.5]}
    assert "1,5 yüzde puan" in change_sentence(mv, TR) and "%38,5" in change_sentence(mv, TR)
    r2 = {"rule": "SR2", "vs_template": "introduced", "confirmed_by_mutation_steps": [0, 2]}
    assert rule_change_sentence(r2, TR) == ("SR2 (karışım karmaşıklığı) şablona kıyasla yeni işaretlendi; doğrulandı: tek başına 1 veya 3 "
                                            "numaralı değişikliklerden herhangi birinin geri alınması işareti kaldırıyor.")
    assert trade_off_sentence("Intent alignment index: template 85.0 -> candidate 90.5 (+5.5 points).", TR) == \
        "Tercihlere Uyum: şablon 85,0 → aday 90,5 (+5,5 puan)."
    sr5 = sr_status({**{f"sr{i}_violation": False for i in range(1, 6)}, "sr5_violation": True, "sr5_hidden_component": "lining",
                     "sr5_trigger_materials": [{"material": "polyester", "pct": 8}]}, "red", TR)[4]
    assert sr5["detail"] == "Katman: astar — yüzeyde bulunmayan malzeme içeriyor: polyester %8."


@pytest.mark.parametrize("lang,expect", [("en", "no TRAIN garments"), ("tr", "TRAIN giysisi yok")])
def test_empty_template_message_in_both_languages(lang, expect):
    r = run({"target_segment": "men"}, lang)
    assert r["status"] == STATUS_NO_TEMPLATES and expect in r["messages"][-1]["text"]


@pytest.mark.parametrize("lang,expect", [("en", "forbidden material"), ("tr", "yasaklı bir malzeme")])
def test_empty_candidate_message_in_both_languages(lang, expect):
    r = generate_recommendations({"target_segment": "men", "detail_category": "shorts", "forbidden_materials": ["cotton"]}, data=DATA,
                                 app_cfg=SMALL, lang=lang)
    assert r["status"] == STATUS_NO_CANDIDATES and expect in r["messages"][-1]["text"]


@pytest.mark.parametrize("req,en_part,tr_part", [
    ({"stretch": "medium"}, "Invalid value for Stretch", "Esneme için geçersiz değer: 'medium' şu seçeneklerden biri değil: 'Esneme yok', 'Düşük', 'Yüksek'"),
    ({"preferred_dominant_material": "kryptonite"}, "Unknown material", "Bilinmeyen malzeme: 'kryptonite'."),
    ({"fit": "skinny"}, "Fit: 'skinny' was removed in V1", "Kesim: 'skinny' V1'de kaldırıldı; bunun yerine 'Dar kesim' kullanın"),
    ({"target_segment": None}, "Please choose a segment.", "Lütfen bir hedef grup seçin."),
    ({"detail_category": "capes"}, "This garment category is not available", "Bu giysi kategorisi CAGO TRAIN verisinde mevcut değil."),
    ({"bogus": 1}, "Unknown field", "Bilinmeyen alan: 'bogus'."),
    ({"water_repellent": "yes"}, "only true or 'No preference' is allowed", "yalnızca evet ya da 'Tercih yok' seçilebilir"),
])
def test_invalid_request_messages_in_both_languages(req, en_part, tr_part):
    e, t = run(req, "en"), run(req, "tr")
    assert e["status"] == t["status"] == STATUS_INVALID
    assert [m["code"] for m in e["messages"]] == [m["code"] for m in t["messages"]]
    assert any(en_part in m["text"] for m in e["messages"]) and any(tr_part in m["text"] for m in t["messages"])
    assert "use null" not in json.dumps(t["messages"]) and "use null" not in json.dumps(e["messages"])


def test_field_unavailability_reasons_are_translatable():
    caps = copy.deepcopy(CAPS)
    caps["categories"]["shorts"]["controls"]["length_cut"] = False
    caps["categories"]["shorts"]["control_decisions"] = {"length_cut": "disabled_insufficient_train_support"}
    a = field_availability("shorts", caps)
    assert TR.t(f"availability.{REASON_CODES[a['length']['reason']]}") == "bu kategori için yeterli sayıda etiketli TRAIN giysisi yok"


# ================================================================ Streamlit: language switch (headless AppTest)
st_testing = pytest.importorskip("streamlit.testing.v1")
APP = str(ROOT / "app" / "streamlit_app.py")


@pytest.fixture
def fixture_app(monkeypatch, tmp_path):
    REP_ALL.to_parquet(tmp_path / "garment_representation.parquet")
    (tmp_path / "ml_material_vocabulary.json").write_text(json.dumps(VOCAB_DOC), encoding="utf-8")
    (tmp_path / "category_capabilities.json").write_text(json.dumps(CAPS), encoding="utf-8")
    monkeypatch.setenv("CAGO_PROCESSED_DIR", str(tmp_path))
    at = st_testing.AppTest.from_file(APP, default_timeout=180)
    at.run()
    assert not at.exception
    return at


def _sb(at):
    return {s.label: s for s in at.sidebar.selectbox}


def _switch(at, lang):
    at.button_group[0].set_value(lang)
    at.run()
    assert not at.exception


def test_english_is_default_and_switcher_is_visible(fixture_app):
    at = fixture_app
    assert at.session_state["cago_lang"] == "en" and at.button_group[0].value == "en"
    assert at.button_group[0].options and at.title[0].value == "CAGO" and "Segment" in _sb(at)


def test_language_switch_preserves_selections_without_regeneration(fixture_app, monkeypatch):
    import app.service as svc
    calls = []
    real = svc.generate_recommendations
    monkeypatch.setattr(svc, "generate_recommendations", lambda *a, **k: calls.append(k.get("lang")) or real(*a, **k))
    at = fixture_app
    _sb(at)["Preferred dominant material"].set_value("linen")
    _sb(at)["Fit"].set_value("relaxed")
    _sb(at)["Breathability"].set_value("high")
    at.run()
    at.sidebar.multiselect[0].set_value(["polyester"])
    at.sidebar.checkbox[0].set_value(True)                                   # moisture wicking
    at.run()
    at.sidebar.button[0].click()
    at.run()
    assert calls == ["en"] and at.session_state["cago_generation_count"] == 1
    en_heads = [s.value for s in at.subheader]
    result_id = id(at.session_state["cago_result"])
    digest = at.session_state["cago_result"]["digest"]

    _switch(at, "tr")
    assert calls == ["en"] and at.session_state["cago_generation_count"] == 1        # no regeneration
    sb = _sb(at)
    assert {k: sb[k].value for k in ("Tercih edilen baskın malzeme", "Kesim", "Nefes alabilirlik", "Hedef grup", "Giysi kategorisi")} == \
        {"Tercih edilen baskın malzeme": "linen", "Kesim": "relaxed", "Nefes alabilirlik": "high", "Hedef grup": "women",
         "Giysi kategorisi": "trousers"}
    assert at.sidebar.multiselect[0].value == ["polyester"] and at.sidebar.checkbox[0].value is True
    tr_heads = [s.value for s in at.subheader]
    assert any("Dengeli" in h for h in tr_heads) and any(h.value == "Pareto adaylarına genel bakış" for h in at.header)
    assert not any("ayarlar değişti" in w.value for w in at.warning)              # language change never makes results stale
    assert at.session_state["cago_result"]["digest"] == digest and id(at.session_state["cago_result"]) == result_id
    texts = " ".join(x.value for x in list(at.markdown) + list(at.caption) + list(at.info) + list(at.warning) + list(at.success))
    assert "Generate recommendations" not in texts and not contains_banned_claim(texts)

    _switch(at, "en")
    assert calls == ["en"] and at.session_state["cago_generation_count"] == 1
    assert [s.value for s in at.subheader] == en_heads
    sb = _sb(at)
    assert (sb["Preferred dominant material"].value, sb["Fit"].value, sb["Breathability"].value) == ("linen", "relaxed", "high")


def test_turkish_form_generates_the_same_recommendation(fixture_app):
    at = fixture_app
    _switch(at, "tr")
    sb = _sb(at)
    assert sb["Kesim"].options[0] == "Tercih yok" and "Rahat kesim" in sb["Kesim"].options
    assert "Keten" in sb["Tercih edilen baskın malzeme"].options
    sb["Tercih edilen baskın malzeme"].set_value("linen")
    sb["Kesim"].set_value("relaxed")
    at.run()
    at.sidebar.button[0].click()
    at.run()
    tr_result = at.session_state["cago_result"]
    assert tr_result["raw_request"] == {"target_segment": "women", "detail_category": "trousers", "preferred_dominant_material": "linen",
                                        "fit": "relaxed"}
    direct = generate_recommendations(tr_result["raw_request"], seed=0, data=DATA, app_cfg=AppConfig())
    assert tr_result["digest"] == direct["digest"] and research_view(tr_result) == research_view(direct)


def test_turkish_empty_state_and_disabled_fields(fixture_app):
    at = fixture_app
    _switch(at, "tr")
    _sb(at)["Hedef grup"].set_value("men")
    at.run()
    assert any("TRAIN giysisi yok" in w.value for w in at.sidebar.warning)
    at.sidebar.button[0].click()
    at.run()
    assert not at.exception and any("TRAIN giysisi yok" in e.value for e in at.error)


def test_turkish_missing_data_screen(monkeypatch, tmp_path):
    monkeypatch.setenv("CAGO_PROCESSED_DIR", str(tmp_path))
    at = st_testing.AppTest.from_file(APP, default_timeout=60)
    at.session_state["cago_lang"] = "tr"
    at.run()
    assert not at.exception and any("Gerekli işlenmiş veri dosyaları" in e.value for e in at.error)
    assert any("TRAIN giysi şablonları" in m.value for m in at.markdown)


def test_turkish_corrupted_data_screen(monkeypatch, tmp_path):
    (tmp_path / "garment_representation.parquet").write_bytes(b"corrupted")
    (tmp_path / "ml_material_vocabulary.json").write_text(json.dumps(VOCAB_DOC), encoding="utf-8")
    (tmp_path / "category_capabilities.json").write_text(json.dumps(CAPS), encoding="utf-8")
    monkeypatch.setenv("CAGO_PROCESSED_DIR", str(tmp_path))
    at = st_testing.AppTest.from_file(APP, default_timeout=60)
    at.session_state["cago_lang"] = "tr"
    at.run()
    assert any("kullanılamıyor" in e.value for e in at.error) and any("okunabilir bir Parquet dosyası değil" in m.value for m in at.markdown)


# ================================================================ demo scenarios / integrity
def test_demo_scenarios_and_recorded_evidence_unchanged():
    from app.demo_scenarios import SCENARIOS
    assert [s["id"] for s in SCENARIOS] == ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]
    assert hashlib.sha256((ROOT / "docs" / "v1_demo_evidence.json").read_bytes()).hexdigest() == \
        "2619d910085925534113522e2603ac55a7115fbfc0cf63958180c98b76275cf3"                                                  # recorded V1.0.0 evidence


@pytest.mark.skipif(not all((PROCESSED / n).is_file() for n in REQUIRED_FILES), reason="processed data missing")
def test_demo_scenarios_reproduce_recorded_evidence_in_both_languages():
    from app.adapters import load_app_data
    from app.demo_scenarios import SCENARIOS, summarise
    data = load_app_data(PROCESSED)
    recorded = {s["id"]: s for s in json.loads((ROOT / "docs" / "v1_demo_evidence.json").read_text(encoding="utf-8"))["scenarios"]}
    for sc in SCENARIOS:
        en_r = generate_recommendations(sc["request"], seed=0, data=data, app_cfg=AppConfig())
        tr_r = generate_recommendations(sc["request"], seed=0, data=data, app_cfg=AppConfig(), lang="tr")
        assert summarise(en_r) == recorded[sc["id"]]["observed"]
        assert research_view(en_r) == research_view(tr_r)


def test_frozen_research_code_unchanged():
    """No frozen research source (cago/, scripts/, tests/) or result file changed; data files that are absent in this checkout
    (git-ignored parquet) are reported by test_frozen_research_files_remain_unchanged."""
    from app.integrity import verify
    v = verify()
    assert v["changed"] == [] and v["added_in_frozen_dirs"] == []
    assert set(v["missing"]) <= {"data/processed/garment_representation.parquet", "data/processed/split_mapping.parquet"}


def test_final_test_manifest_hashes_of_sources_and_results():
    from cago.benchmark.final_test_manifest import file_sha256
    m = json.loads((ROOT / "configs" / "final_test_evaluation_manifest.json").read_text(encoding="utf-8"))
    bad = [rel for rel, h in {**m["frozen_files"], **m["new_evaluation_code"]}.items() if file_sha256(ROOT / rel) != h]
    assert bad == []
    for sect in ("prior_results",):
        assert [n for n, h in m[sect].items() if (PROCESSED / n).exists() and file_sha256(PROCESSED / n) != h] == []
    snap = json.loads((ROOT / "app" / "frozen_research_hashes.json").read_text(encoding="utf-8"))["files"]
    for rel in ("configs/final_test_evaluation_manifest.json", "data/processed/final_test_evaluation_report.json",
                "data/processed/final_test_evaluation_report.md"):
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == snap[rel]
