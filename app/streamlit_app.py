"""CAGO Demo App V1 (Streamlit).  Run from the project root:

    streamlit run app/streamlit_app.py

All research logic lives in the frozen `cago` package; this file only collects input and renders the service output.
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

from app.adapters import (DEFAULT_PROCESSED_DIR, MissingDataError, enum_options, field_availability, form_to_raw_request,  # noqa: E402
                          load_app_data)
from app.presenters import DISCLAIMER, ROLE_TITLES, fmt_pct  # noqa: E402
from app.service import FINAL_TEST_BUDGET, STATUS_OK, AppConfig, generate_recommendations  # noqa: E402
from app.state import DEFAULT_SEED, current_result, result_is_stale, store_result  # noqa: E402

PROCESSED_DIR = Path(os.environ.get("CAGO_PROCESSED_DIR", DEFAULT_PROCESSED_DIR))
NO_PREF = "No preference"
COLOR_FRONT, COLOR_OTHER = "#2a78d6", "#b4b2a9"

st.set_page_config(page_title="CAGO demo", layout="wide")


@st.cache_resource(show_spinner="Loading TRAIN templates and support tables ...")
def get_data(processed_dir: str):
    return load_app_data(Path(processed_dir))


def opt(v):
    return None if v in (None, NO_PREF) else v


def header() -> None:
    st.title("CAGO")
    st.markdown("**Constraint-Aware Garment Optimization** · choose garment requirements, and CAGO adapts real TRAIN garment templates "
                "to fit them while screening every candidate with the SR1–SR5 textile-sorting rules.")
    with st.container(border=True):
        st.caption("Prototype notice · " + " ".join(DISCLAIMER))


def missing_data_screen(err: MissingDataError) -> None:
    st.error(f"Required processed data files are missing in `{err.processed_dir}`.")
    st.markdown("\n".join(f"- `{n}`: {why}" for n, why in err.missing.items()))
    st.markdown("See `docs/DEMO_APP.md` (section *Required data files*). You can point the app to another folder with the "
                "`CAGO_PROCESSED_DIR` environment variable.")


def sidebar(data):
    st.sidebar.header("Your garment")
    segs = data.segments()
    seg = st.sidebar.selectbox("Segment", segs, index=0)
    all_cats = sorted({c for s in data.cells.values() for c in s})
    cell_counts = data.cells.get(seg, {})
    cat = st.sidebar.selectbox("Garment category", all_cats, index=all_cats.index("trousers") if "trousers" in all_cats else 0,
                               format_func=lambda c: c.replace("_", " ") + ("" if cell_counts.get(c) else "  (no TRAIN templates)"))
    if not cell_counts.get(cat):
        st.sidebar.warning("There are no TRAIN garments for this segment and category, so CAGO cannot generate designs for it.")
    avail = field_availability(cat, data.capabilities)
    mats = data.materials_for(cat)
    colours = data.colours.get((seg, cat), [])

    with st.sidebar.form("prefs"):
        st.subheader("Materials")
        pref = st.selectbox("Preferred dominant material", [NO_PREF] + mats, help="Materials seen in TRAIN garments of this category.")
        forb = st.multiselect("Forbidden materials", mats, help="Hard constraint: these materials never appear in a recommendation.")
        st.subheader("Look")
        col = st.selectbox("Colour", [NO_PREF] + [c for c, _ in colours[:40]],
                           help="Colours of TRAIN templates in this cell. CAGO V1 does not recolour garments: colour is inherited from the template.")
        form = {"segment": seg, "category": cat, "preferred_material": opt(pref), "forbidden_materials": forb, "colour": opt(col)}
        for f, label in (("fit", "Fit"), ("length", "Length")):
            a = avail[f]
            form[f] = opt(st.selectbox(label, [NO_PREF, *enum_options(f)], disabled=not a["enabled"],
                                       help=None if a["enabled"] else f"Unavailable: {a['reason']}."))
        st.subheader("Functional preferences")
        st.caption("Composition-based proxies, not measured performance.")
        for f, label in (("stretch", "Stretch"), ("thermal_warmth", "Thermal warmth"), ("breathability", "Breathability"), ("durability", "Durability")):
            a = avail[f]
            form[f] = opt(st.selectbox(label, [NO_PREF, *enum_options(f)], disabled=not a["enabled"],
                                       help=None if a["enabled"] else f"Unavailable: {a['reason']}."))
        for f, label in (("moisture_wicking", "Moisture wicking"), ("water_repellent", "Water repellency")):
            a = avail[f]
            form[f] = True if st.checkbox(label, disabled=not a["enabled"], help=None if a["enabled"] else f"Unavailable: {a['reason']}.") else None
        unavailable = [label for f, label in (("fit", "fit"), ("length", "length"), ("stretch", "stretch"), ("thermal_warmth", "thermal warmth"),
                                              ("breathability", "breathability"), ("durability", "durability"), ("moisture_wicking", "moisture wicking"),
                                              ("water_repellent", "water repellency")) if not avail[f]["enabled"]]
        if unavailable:
            st.caption("Unavailable for this category: " + ", ".join(unavailable) + ".")
        with st.expander("Advanced"):
            seed = st.number_input("Reproducibility seed", min_value=0, max_value=10_000, value=DEFAULT_SEED, step=1)
            n_t = st.slider("Templates", 1, 20, FINAL_TEST_BUDGET["n_templates"])
            per_t = st.slider("Candidates per template", 1, 20, FINAL_TEST_BUDGET["candidates_per_template"])
            st.caption(f"Default budget equals the final TEST evaluation budget ({FINAL_TEST_BUDGET['n_templates']} × "
                       f"{FINAL_TEST_BUDGET['candidates_per_template']}). The budget is an app setting; it does not change the frozen generator.")
        submitted = st.form_submit_button("Generate recommendations", type="primary", width="stretch")
    return form, int(seed), AppConfig(n_templates=n_t, candidates_per_template=per_t), submitted


def show_messages(result) -> None:
    for m in result["messages"]:
        {"error": st.error, "warning": st.warning}.get(m["level"], st.info)(m["text"])


def status_line(result) -> None:
    s = result["stats"]
    parts = [f"generated in {s.get('seconds_total', 0):.1f} s"]
    if "candidates_generated" in s:
        parts.append(f"{s['candidates_generated']} of {s['candidates_requested']} requested candidates")
    if "hard_valid" in s:
        parts.append(f"{s['hard_valid']} hard-valid")
    if "front_size" in s:
        parts.append(f"{s['front_size']} on the Pareto front")
    if "eligible_templates" in s:
        parts.append(f"{s['templates_used']} of {s['eligible_templates']} eligible TRAIN templates used")
    st.caption(" · ".join(parts) + f" · seed {result['seed']}")


def card(rec) -> None:
    with st.container(border=True):
        st.subheader(" + ".join(rec["role_titles"]))
        if len(rec["roles"]) > 1:
            st.caption("The same candidate fulfils " + " and ".join(rec["role_titles"]) + ".")
        st.markdown(f"**{rec['category'].capitalize()}** · colour: {rec['colour'] or 'n/a'} · fit: {rec['fit'] or 'not labelled'} · "
                    f"length: {rec['length'] or 'not labelled'}")
        for c in rec["composition"]:
            st.markdown(f"- *{c['component']}*: " + ", ".join(f"{m['material']} {fmt_pct(m['pct'])}" for m in c["materials"]))
        if rec["display_merged_duplicate_slots"]:
            st.caption("Identical materials listed in several slots of one component are merged for display.")
        m1, m2, m3 = st.columns(3)
        m1.metric("Intent alignment", "n/a" if rec["intent_0_100"] is None else f"{rec['intent_0_100']:.0f}")
        m2.metric("Plausibility", f"{rec['plausibility_0_100']:.0f}")
        m3.metric("SR violations", f"{rec['violation_count']} / 5")
        (st.success if rec["violation_count"] == 0 else st.warning)(rec["sorting_summary"])
        for line in rec["headline"][:-1]:
            st.markdown(f"- {line}")
        with st.expander("Why this recommendation"):
            for r in rec["role_reasons"]:
                st.markdown(f"- {r}")
            for c in rec["comparisons"]:
                st.markdown(f"- {c}")
            if rec["preferences"]:
                st.markdown("**Your preferences**")
                for p in rec["preferences"]:
                    st.markdown(f"- {p['preference']} = `{p['requested']}`: **{p['status']}**. {p['explanation']}.")
        with st.expander("SR1–SR5 sorting-screening results"):
            for r in rec["sr"]:
                st.markdown(f"- {'⚠️' if r['violated'] else '✅'} **{r['rule']} · {r['name']}**: {r['status']}. {r['detail']}")
        with st.expander("Changes from the TRAIN template"):
            st.caption(f"Template garment `{rec['template_garment_id']}` · {rec['template_distance']['n_substitutions']} substitution(s), "
                       f"{rec['template_distance']['abs_pct_change_total']:g} percentage points moved.")
            for m in rec["changes_from_template"]:
                st.markdown(f"- {m}")
            for s in rec["confirmed_rule_changes"]:
                st.markdown(f"- {s}")
            for s in rec["trade_offs_vs_template"]:
                st.markdown(f"- {s}")


def pareto_chart(result) -> None:
    df = pd.DataFrame(result["pareto_points"])
    if df.empty:
        return
    df["group"] = df["is_pareto"].map({True: "Pareto front", False: "Other candidates"})
    df["role"] = df["roles"].map(lambda r: " + ".join(r))
    has_intent = df["intent_0_100"].notna().any()
    xfield, xtitle = ("intent_0_100", "Intent alignment (0–100)") if has_intent else ("violation_count", "SR1–SR5 violations")
    if not has_intent:
        st.caption("No scorable preference was given, so the chart shows violations instead of intent alignment.")
    base = alt.Chart(df).encode(
        x=alt.X(f"{xfield}:Q", title=xtitle, scale=alt.Scale(zero=False)),
        y=alt.Y("plausibility_0_100:Q", title="Dataset-relative plausibility (0–100)", scale=alt.Scale(zero=False)),
        tooltip=[alt.Tooltip("candidate_id:N", title="candidate"), alt.Tooltip("intent_0_100:Q", title="intent", format=".0f"),
                 alt.Tooltip("plausibility_0_100:Q", title="plausibility", format=".0f"), alt.Tooltip("violation_count:Q", title="SR violations"),
                 alt.Tooltip("role:N", title="recommended as")])
    pts = base.mark_circle(size=70, stroke="white", strokeWidth=1).encode(
        color=alt.Color("group:N", scale=alt.Scale(domain=["Pareto front", "Other candidates"], range=[COLOR_FRONT, COLOR_OTHER]),
                        legend=alt.Legend(title=None, orient="top")),
        opacity=alt.condition(alt.datum.is_pareto, alt.value(1.0), alt.value(0.55)))
    vio = base.transform_filter(alt.datum.is_pareto).mark_text(dy=-17, fontSize=11, color="#52514e").encode(text=alt.Text("violation_count:Q"))
    sel = base.transform_filter(alt.datum.role != "").mark_point(size=260, shape="circle", filled=False, color="#0b0b0b", strokeWidth=1.5)
    lab = base.transform_filter(alt.datum.role != "").mark_text(dx=12, align="left", fontSize=12, fontWeight="bold", color="#0b0b0b").encode(text="role:N")
    st.altair_chart((pts + vio + sel + lab).properties(height=360), width="stretch")
    st.caption("Each dot is an evaluated hard-valid candidate. Numbers above Pareto-front dots are SR1–SR5 violation counts; "
               "circled dots are the recommendations.")
    with st.expander("Candidate table"):
        st.dataframe(df[["candidate_id", "intent_0_100", "plausibility_0_100", "violation_count", "is_pareto", "role"]]
                     .sort_values(["is_pareto", "violation_count"], ascending=[False, True]), width="stretch", hide_index=True)


def technical_details(result) -> None:
    with st.expander("Technical details"):
        st.markdown(f"- {result['config_note']}\n- Budget: {result['budget']['n_templates']} templates × "
                    f"{result['budget']['candidates_per_template']} candidates · seed {result['seed']} (demo setting; it does not reproduce "
                    "the final TEST benchmark).\n- Generation, evaluation and support statistics use TRAIN garments only.")
        st.markdown("**SR1–SR5 screening rules**")
        from app.presenters import SR_RULES
        for r, (name, txt) in SR_RULES.items():
            st.markdown(f"- **{r} · {name}**: {txt}")
        st.markdown("**Normalised request**")
        st.code(json.dumps(result["request"] or result["raw_request"], indent=1, default=str), language="json")
        st.markdown("**Run statistics**")
        st.code(json.dumps(result["stats"], indent=1, default=str), language="json")


def main() -> None:
    header()
    try:
        data = get_data(str(PROCESSED_DIR))
    except MissingDataError as err:
        missing_data_screen(err)
        return
    form, seed, cfg, submitted = sidebar(data)
    raw = form_to_raw_request(form)
    if submitted:
        bar = st.progress(0.0, text="Starting ...")
        result = generate_recommendations(form, seed=seed, data=data, app_cfg=cfg, is_form=True,
                                          progress=lambda text, frac: bar.progress(frac, text=text))
        bar.empty()
        store_result(st.session_state, result)
    result = current_result(st.session_state)
    if result is None:
        st.info("Choose your requirements in the sidebar and press **Generate recommendations**.")
        return
    if result_is_stale(st.session_state, raw, seed, {"n_templates": cfg.n_templates, "candidates_per_template": cfg.candidates_per_template}):
        st.warning("The settings changed since these results were generated. Press **Generate recommendations** to update them.")
    status_line(result)
    show_messages(result)
    if result["status"] != STATUS_OK:
        technical_details(result)
        return
    recs = result["recommendations"]
    cols = st.columns(len(recs))
    for c, rec in zip(cols, recs):
        with c:
            card(rec)
    st.header("Pareto candidate overview")
    pareto_chart(result)
    technical_details(result)


main()
