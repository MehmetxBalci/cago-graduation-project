"""CAGO Demo App V1.1 (Streamlit, English / Turkish).  Run from the project root:

    streamlit run app/streamlit_app.py

All research logic lives in the frozen `cago` package; this file only collects input and renders the service output.

Localization (V1.1.0)
* The TR / EN switcher (upper right) only changes the wording. Every input widget has a stable key, its options are the
  internal identifiers (`cotton`, `relaxed`, ...) and only `format_func` translates them, so the request sent to the
  generator is identical in both languages.
* Switching the language re-asserts the current internal widget values (Streamlit matches widget values by their displayed
  label), so selections are preserved; it never calls the generator. The stored research result is re-rendered in the
  selected language with `localize_result`.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import altair as alt  # noqa: E402  (bundled with Streamlit)
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from app.adapters import (DEFAULT_PROCESSED_DIR, REASON_CODES, DataLoadError, MissingDataError, enum_options, field_availability,  # noqa: E402
                          form_to_raw_request, load_app_data)
from app.i18n import DEFAULT_LANGUAGE, LANGUAGE_BUTTONS, SUPPORTED_LANGUAGES, Translator, get_translator  # noqa: E402
from app.presenters import disclaimer, materials_text, roles_text, sr_rules  # noqa: E402
from app.service import FINAL_TEST_BUDGET, STATUS_OK, AppConfig, generate_recommendations, localize_result  # noqa: E402
from app.state import (DEFAULT_SEED, GENERATION_COUNT_KEY, LANG_KEY, current_result, record_generation, result_is_stale,  # noqa: E402
                       store_result)

PROCESSED_DIR = Path(os.environ.get("CAGO_PROCESSED_DIR", DEFAULT_PROCESSED_DIR))
NO_PREF = "No preference"                      # internal sentinel option (displayed via the catalog), never sent to the engine
COLOR_FRONT, COLOR_OTHER = "#2a78d6", "#b4b2a9"
ENUM_FIELDS = ("fit", "length", "stretch", "thermal_warmth", "breathability", "durability")
BOOL_FIELDS = ("moisture_wicking", "water_repellent")
UNAVAILABLE_ORDER = ("fit", "length", "stretch", "thermal_warmth", "breathability", "durability", "moisture_wicking", "water_repellent")
KEYS = {f: f"w_{f}" for f in ("segment", "category", "preferred_material", "forbidden_materials", "colour", *ENUM_FIELDS, *BOOL_FIELDS,
                               "seed", "n_templates", "per_template")}
ENUM_DOMAIN = {"fit": "fit", "length": "length_cut", "stretch": "stretch", "thermal_warmth": "thermal_warmth",
               "breathability": "breathability", "durability": "durability_wear"}

if LANG_KEY not in st.session_state:
    st.session_state[LANG_KEY] = DEFAULT_LANGUAGE
st.set_page_config(page_title=get_translator(st.session_state.get(LANG_KEY) or DEFAULT_LANGUAGE).t("app.page_title"), layout="wide")


@st.cache_resource(show_spinner=False)
def get_data(processed_dir: str):
    return load_app_data(Path(processed_dir))


def opt(v):
    return None if v in (None, NO_PREF) else v


def keep_selections() -> None:
    """Language-switch callback: re-assert every input's INTERNAL value so the widgets keep it under the new labels.
    Runs before the script; it never triggers generation."""
    for k in KEYS.values():
        if k in st.session_state:
            st.session_state[k] = st.session_state[k]
    if not st.session_state.get(LANG_KEY):                 # a segmented control can be clicked off; keep a language
        st.session_state[LANG_KEY] = st.session_state.get("_cago_prev_lang", DEFAULT_LANGUAGE)


def language() -> Translator:
    lang = st.session_state.get(LANG_KEY) or DEFAULT_LANGUAGE
    st.session_state["_cago_prev_lang"] = lang
    return get_translator(lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE)


def header() -> Translator:
    left, right = st.columns([6, 1], vertical_alignment="center")
    with right:
        st.segmented_control(get_translator(st.session_state.get(LANG_KEY) or DEFAULT_LANGUAGE).t("app.language_label"),
                             list(SUPPORTED_LANGUAGES), format_func=LANGUAGE_BUTTONS.get, key=LANG_KEY, required=True,
                             on_change=keep_selections, label_visibility="collapsed",
                             help=get_translator(st.session_state.get(LANG_KEY) or DEFAULT_LANGUAGE).t("app.language_help"))
    tr = language()
    with left:
        st.title(tr.t("app.title"))
    st.markdown(tr.t("app.subtitle"))
    with st.container(border=True):
        st.caption(tr.t("app.prototype_notice") + " ".join(disclaimer(tr)))
    return tr


def missing_data_screen(err: MissingDataError, tr: Translator) -> None:
    st.error(tr.t("data.missing_title", dir=err.processed_dir))
    st.markdown("\n".join(f"- `{n}`: {tr.t('data.file.' + n) if tr.has('data.file.' + n) else why}" for n, why in err.missing.items()))
    st.markdown(tr.t("data.missing_help"))


def data_error_screen(err: DataLoadError, tr: Translator) -> None:
    st.error(tr.t("data.error_title", dir=err.processed_dir, file=err.file))
    key = f"data.problem.{err.code}"
    problem = tr.t(key, **err.params) if err.code and tr.has(key) else err.problem
    st.markdown(tr.t("data.problem_line", problem=problem))
    st.markdown(tr.t("data.error_help"))


def _default(name: str, value) -> None:
    if name not in st.session_state:
        st.session_state[name] = value


def _unavailable_help(a: dict, tr: Translator) -> str | None:
    if a["enabled"]:
        return None
    code = REASON_CODES.get(a["reason"])
    return tr.t("form.unavailable_help", reason=tr.t(f"availability.{code}") if code else a["reason"])


def _fmt(labels: dict, tr: Translator):
    return lambda v: tr.t("form.no_preference") if v == NO_PREF else labels.get(v, str(v))


def sidebar(data, tr: Translator):
    sb = st.sidebar
    sb.header(tr.t("form.header"))
    segs = data.segments()
    _default(KEYS["segment"], segs[0])
    seg = sb.selectbox(tr.field("segment"), segs, key=KEYS["segment"], format_func=_fmt(tr.option_labels("segment", segs), tr))
    all_cats = sorted({c for s in data.cells.values() for c in s})
    cell_counts = data.cells.get(seg, {})
    _default(KEYS["category"], "trousers" if "trousers" in all_cats else all_cats[0])
    cat_labels = tr.option_labels("category", all_cats)
    cat = sb.selectbox(tr.field("category"), all_cats, key=KEYS["category"],
                       format_func=lambda c: cat_labels[c] + ("" if cell_counts.get(c) else tr.t("form.no_templates_suffix")))
    if not cell_counts.get(cat):
        sb.warning(tr.t("form.no_templates_warning"))
    avail = field_availability(cat, data.capabilities)
    mats = data.materials_for(cat)
    colours = [c for c, _ in data.colours.get((seg, cat), [])[:40]]
    mat_labels = tr.option_labels("material", mats)

    sb.subheader(tr.t("form.section.materials"))
    _default(KEYS["preferred_material"], NO_PREF)
    pref = sb.selectbox(tr.field("preferred_material"), [NO_PREF] + mats, key=KEYS["preferred_material"], format_func=_fmt(mat_labels, tr),
                        help=tr.t("form.help.preferred_material"))
    _default(KEYS["forbidden_materials"], [])
    if any(m not in mats for m in st.session_state[KEYS["forbidden_materials"]]):    # options changed with the category
        st.session_state[KEYS["forbidden_materials"]] = [m for m in st.session_state[KEYS["forbidden_materials"]] if m in mats]
    forb = sb.multiselect(tr.field("forbidden_materials"), mats, key=KEYS["forbidden_materials"], format_func=_fmt(mat_labels, tr),
                          help=tr.t("form.help.forbidden_materials"), placeholder=tr.t("form.choose_options"))
    sb.subheader(tr.t("form.section.look"))
    _default(KEYS["colour"], NO_PREF)
    col = sb.selectbox(tr.field("colour"), [NO_PREF] + colours, key=KEYS["colour"], format_func=_fmt(tr.option_labels("colour", colours), tr),
                       help=tr.t("form.help.colour"))
    form = {"segment": seg, "category": cat, "preferred_material": opt(pref), "forbidden_materials": forb, "colour": opt(col)}

    def enum_select(f: str):
        a = avail[f]
        _default(KEYS[f], NO_PREF)
        if not a["enabled"]:
            st.session_state[KEYS[f]] = NO_PREF                 # a disabled field never keeps a stale value
        values = list(enum_options(f))
        form[f] = opt(sb.selectbox(tr.field(f), [NO_PREF, *values], key=KEYS[f], disabled=not a["enabled"],
                                   format_func=_fmt(tr.option_labels(ENUM_DOMAIN[f], values), tr), help=_unavailable_help(a, tr)))

    for f in ("fit", "length"):
        enum_select(f)
    sb.subheader(tr.t("form.section.functional"))
    sb.caption(tr.t("form.functional_caption"))
    for f in ("stretch", "thermal_warmth", "breathability", "durability"):
        enum_select(f)
    for f in BOOL_FIELDS:
        a = avail[f]
        _default(KEYS[f], False)
        if not a["enabled"]:
            st.session_state[KEYS[f]] = False
        form[f] = True if sb.checkbox(tr.field(f), key=KEYS[f], disabled=not a["enabled"], help=_unavailable_help(a, tr)) else None
    unavailable = [tr.field_lc(f) for f in UNAVAILABLE_ORDER if not avail[f]["enabled"]]
    if unavailable:
        sb.caption(tr.t("form.unavailable_list", fields=", ".join(unavailable)))
    with sb.expander(tr.t("form.advanced")):
        _default(KEYS["seed"], DEFAULT_SEED)
        _default(KEYS["n_templates"], FINAL_TEST_BUDGET["n_templates"])
        _default(KEYS["per_template"], FINAL_TEST_BUDGET["candidates_per_template"])
        seed = st.number_input(tr.t("form.seed"), min_value=0, max_value=10_000, step=1, key=KEYS["seed"])
        n_t = st.slider(tr.t("form.templates"), 1, 20, key=KEYS["n_templates"])
        per_t = st.slider(tr.t("form.candidates_per_template"), 1, 20, key=KEYS["per_template"])
        st.caption(tr.t("form.budget_caption", n_templates=FINAL_TEST_BUDGET["n_templates"], per_template=FINAL_TEST_BUDGET["candidates_per_template"]))
    submitted = sb.button(tr.t("form.generate"), type="primary", width="stretch", key="cago_generate")
    return form, int(seed), AppConfig(n_templates=n_t, candidates_per_template=per_t), submitted


def show_messages(result) -> None:
    for m in result["messages"]:
        {"error": st.error, "warning": st.warning}.get(m["level"], st.info)(m["text"])


def status_line(result, tr: Translator) -> None:
    s = result["stats"]
    parts = [tr.t("status.generated_in", seconds=tr.num(s.get("seconds_total", 0), ".1f"))]
    if "candidates_generated" in s:
        parts.append(tr.t("status.candidates", generated=s["candidates_generated"], requested=s["candidates_requested"]))
    if "hard_valid" in s:
        parts.append(tr.t("status.hard_valid", n=s["hard_valid"]))
    if "front_size" in s:
        parts.append(tr.t("status.front", n=s["front_size"]))
    if "eligible_templates" in s:
        parts.append(tr.t("status.templates", used=s["templates_used"], eligible=s["eligible_templates"]))
    st.caption(" · ".join(parts) + tr.t("status.seed", seed=result["seed"]))


def card(rec, tr: Translator) -> None:
    with st.container(border=True):
        st.subheader(" + ".join(rec["role_titles"]))
        if len(rec["roles"]) > 1:
            st.caption(tr.t("card.same_candidate", roles=roles_text(rec["roles"], tr, "role.and")))
        st.markdown(tr.t("card.summary", category=rec["category"][:1].upper() + rec["category"][1:],
                         colour=tr.label("colour", rec["colour"]) if rec["colour"] else tr.t("card.na"),
                         fit=tr.label("fit", rec["fit"]) if rec["fit"] else tr.t("card.not_labelled"),
                         length=tr.label("length_cut", rec["length"]) if rec["length"] else tr.t("card.not_labelled")))
        for c in rec["composition"]:
            st.markdown(f"- *{c['component']}*: " + materials_text(c["materials"], tr))
        if rec["display_merged_duplicate_slots"]:
            st.caption(tr.t("card.merged_caption"))
        m1, m2, m3 = st.columns(3)
        m1.metric(tr.t("card.metric.intent"), tr.t("card.na") if rec["intent_0_100"] is None else f"{rec['intent_0_100']:.0f}",
                  help=tr.t("card.metric.intent_help"))
        m2.metric(tr.t("card.metric.plausibility"), f"{rec['plausibility_0_100']:.0f}", help=tr.t("card.metric.plausibility_help"))
        m3.metric(tr.t("card.metric.violations"), tr.t("card.violations_value", n=rec["violation_count"]), help=tr.t("card.metric.violations_help"))
        (st.success if rec["violation_count"] == 0 else st.warning)(rec["sorting_summary"])
        for line in rec["headline"][:-1]:
            st.markdown(f"- {line}")
        with st.expander(tr.t("card.why")):
            for r in rec["role_reasons"]:
                st.markdown(f"- {r}")
            for c in rec["comparisons"]:
                st.markdown(f"- {c}")
            if rec["preferences"]:
                st.markdown(tr.t("card.your_preferences"))
                for p in rec["preferences"]:
                    st.markdown(tr.t("card.preference_line", preference=p["preference"], requested=p["requested"], status=p["status"],
                                     explanation=p["explanation"]))
                    st.caption(tr.t("card.technical_evidence", text=p["technical"]))
        with st.expander(tr.t("card.sr_expander")):
            for r in rec["sr"]:
                st.markdown(tr.t("card.sr_line", icon="⚠️" if r["violated"] else "✅", rule=r["rule"], name=r["name"], status=r["status"],
                                 detail=r["detail"]))
        with st.expander(tr.t("card.changes_expander")):
            td = rec["template_distance"]
            st.caption(tr.t("card.template_caption", template=rec["template_garment_id"], n_subs=td["n_substitutions"],
                            abs_change=tr.num(td["abs_pct_change_total"], "g")))
            for m in rec["changes_from_template"]:
                st.markdown(f"- {m}")
            for s in rec["confirmed_rule_changes"]:
                st.markdown(f"- {s}")
            for s in rec["trade_offs_vs_template"]:
                st.markdown(f"- {s}")


def pareto_chart(result, tr: Translator) -> None:
    df = pd.DataFrame(result["pareto_points"])
    if df.empty:
        return
    front, other = tr.t("chart.group.front"), tr.t("chart.group.other")
    df["group"] = df["is_pareto"].map({True: front, False: other})
    df["role"] = df["roles"].map(lambda r: " + ".join(r))
    has_intent = df["intent_0_100"].notna().any()
    xfield, xtitle = ("intent_0_100", tr.t("chart.axis.intent")) if has_intent else ("violation_count", tr.t("chart.axis.violations"))
    if not has_intent:
        st.caption(tr.t("chart.no_intent_axis"))
    elif df["intent_0_100"].isna().any():
        st.caption(tr.t("chart.unplotted", n=int(df["intent_0_100"].isna().sum())))
    base = alt.Chart(df).encode(
        # fixed domains: intent is always 0-100 and violations 0-5, so identical values (e.g. every candidate at intent 0) still give a
        # readable axis instead of a degenerate one
        x=alt.X(f"{xfield}:Q", title=xtitle, scale=alt.Scale(domain=[0, 100] if has_intent else [0, 5]),
                axis=alt.Axis(format="d", tickMinStep=1)),
        y=alt.Y("plausibility_0_100:Q", title=tr.t("chart.axis.plausibility"), scale=alt.Scale(zero=False)),
        tooltip=[alt.Tooltip("candidate_id:N", title=tr.t("chart.tooltip.candidate")),
                 alt.Tooltip("intent_0_100:Q", title=tr.t("chart.tooltip.intent"), format=".0f"),
                 alt.Tooltip("plausibility_0_100:Q", title=tr.t("chart.tooltip.plausibility"), format=".0f"),
                 alt.Tooltip("violation_count:Q", title=tr.t("chart.tooltip.violations")),
                 alt.Tooltip("role:N", title=tr.t("chart.tooltip.role"))])
    pts = base.mark_circle(size=70, stroke="white", strokeWidth=1).encode(
        color=alt.Color("group:N", scale=alt.Scale(domain=[front, other], range=[COLOR_FRONT, COLOR_OTHER]),
                        legend=alt.Legend(title=None, orient="top")),
        opacity=alt.condition(alt.datum.is_pareto, alt.value(1.0), alt.value(0.55)))
    vio = base.transform_filter(alt.datum.is_pareto).mark_text(dy=-17, fontSize=11, color="#52514e").encode(text=alt.Text("violation_count:Q"))
    sel = base.transform_filter(alt.datum.role != "").mark_point(size=260, shape="circle", filled=False, color="#0b0b0b", strokeWidth=1.5)
    lab = base.transform_filter(alt.datum.role != "").mark_text(dx=12, align="left", fontSize=12, fontWeight="bold", color="#0b0b0b").encode(text="role:N")
    st.altair_chart((pts + vio + sel + lab).properties(height=360), width="stretch")
    st.caption(tr.t("chart.caption"))
    with st.expander(tr.t("chart.table_expander")):
        cols = {"candidate_id": "chart.col.candidate_id", "intent_0_100": "chart.col.intent", "plausibility_0_100": "chart.col.plausibility",
                "violation_count": "chart.col.violations", "is_pareto": "chart.col.is_pareto", "role": "chart.col.role"}
        table = df[list(cols)].sort_values(["is_pareto", "violation_count"], ascending=[False, True])
        st.dataframe(table.rename(columns={k: tr.t(v) for k, v in cols.items()}), width="stretch", hide_index=True)


def technical_details(result, tr: Translator) -> None:
    with st.expander(tr.t("tech.expander")):
        st.markdown(f"- {result['config_note']}\n- " + tr.t("tech.budget", n_templates=result['budget']['n_templates'],
                                                             per_template=result['budget']['candidates_per_template'], seed=result['seed'])
                    + "\n- " + tr.t("tech.train_only"))
        st.markdown(tr.t("tech.sr_rules"))
        for r, (name, txt) in sr_rules(tr).items():
            st.markdown(tr.t("tech.sr_rule_line", rule=r, name=name, text=txt))
        st.markdown(tr.t("tech.request"))
        st.code(json.dumps(result["request"] or result["raw_request"], indent=1, default=str), language="json")
        st.markdown(tr.t("tech.stats"))
        st.code(json.dumps({**result["stats"], "digest": result.get("digest")}, indent=1, default=str), language="json")


def localized_view(result, tr: Translator):
    """The stored research result rendered in the active language (cached per result and language; no regeneration)."""
    if result.get("lang") == tr.lang:
        return result
    cache = st.session_state.get("_cago_view")
    if cache and cache[0] is result and cache[1] == tr.lang:
        return cache[2]
    view = localize_result(result, tr.lang)
    st.session_state["_cago_view"] = (result, tr.lang, view)
    return view


def main() -> None:
    tr = header()
    try:
        with st.spinner(tr.t("app.loading_data")):
            data = get_data(str(PROCESSED_DIR))
    except MissingDataError as err:
        missing_data_screen(err, tr)
        return
    except DataLoadError as err:
        data_error_screen(err, tr)
        return
    form, seed, cfg, submitted = sidebar(data, tr)
    raw = form_to_raw_request(form)
    if submitted:
        bar = st.progress(0.0, text=tr.t("app.progress_start"))
        result = generate_recommendations(form, seed=seed, data=data, app_cfg=cfg, is_form=True, lang=tr.lang,
                                          progress=lambda text, frac: bar.progress(frac, text=text))
        bar.empty()
        store_result(st.session_state, result)
        record_generation(st.session_state)
    result = current_result(st.session_state)
    if result is None:
        st.info(tr.t("app.start_hint"))
        return
    view = localized_view(result, tr)
    if result_is_stale(st.session_state, raw, seed, {"n_templates": cfg.n_templates, "candidates_per_template": cfg.candidates_per_template}):
        st.warning(tr.t("app.stale_results"))
    status_line(view, tr)
    show_messages(view)
    if view["status"] != STATUS_OK:
        technical_details(view, tr)
        return
    recs = view["recommendations"]
    cols = st.columns(len(recs))
    for c, rec in zip(cols, recs):
        with c:
            card(rec, tr)
    st.header(tr.t("app.pareto_header"))
    pareto_chart(view, tr)
    technical_details(view, tr)


main()
