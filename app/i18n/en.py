"""English UI catalog (source language, default).

Every user-facing string of the Streamlit app lives here under a stable key. Placeholders use `str.format` syntax
(`{name}`); the Turkish catalog (`tr.py`) must define exactly the same keys with the same placeholders (tested).

The English texts reproduce the V1.0.0 wording exactly (tested against app/tests/golden_en_v1.json).
Internal identifiers (materials, colours, categories, enum values, component names) are English already, so the English
vocabulary rendering is the identity (categories / components: underscores shown as spaces) -- see translator.py.
"""
from __future__ import annotations

LANGUAGE_NAME = "English"

MESSAGES: dict[str, str] = {
    # ------------------------------------------------------------ page / header
    "app.page_title": "CAGO demo",
    "app.title": "CAGO",
    "app.subtitle": ("**Constraint-Aware Garment Optimization** · choose garment requirements, and CAGO adapts real TRAIN garment templates "
                     "to fit them while screening every candidate with the SR1–SR5 textile-sorting rules."),
    "app.prototype_notice": "Prototype notice · ",
    "app.loading_data": "Loading TRAIN templates and support tables ...",
    "app.language_label": "Language",
    "app.language_help": "Switch the interface language. Only the wording changes: the request, the generated candidates and all scores stay the same.",
    "app.start_hint": "Choose your requirements in the sidebar and press **Generate recommendations**.",
    "app.stale_results": "The settings changed since these results were generated. Press **Generate recommendations** to update them.",
    "app.pareto_header": "Pareto candidate overview",
    "app.progress_start": "Starting ...",

    # ------------------------------------------------------------ disclaimer (shown in the header box)
    "disclaimer.1": "CAGO is a graduation-project prototype.",
    "disclaimer.2": "Sorting results refer only to the SR1–SR5 screening rules.",
    "disclaimer.3": "Zero detected violations does not guarantee recyclability or manufacturability.",
    "disclaimer.4": "Plausibility is dataset-relative: it measures support and similarity relative to the TRAIN dataset.",
    "disclaimer.5": "Recommendations are generated from patterns and support found in the TRAIN dataset.",

    # ------------------------------------------------------------ data-file screens
    "data.missing_title": "Required processed data files are missing in `{dir}`.",
    "data.missing_help": ("See `docs/DEMO_APP.md` (section *Required data files*). You can point the app to another folder with the "
                          "`CAGO_PROCESSED_DIR` environment variable."),
    "data.file.garment_representation.parquet": ("TRAIN garment templates (component compositions, labels, split column); built by "
                                                 "scripts/run_representation.py"),
    "data.file.ml_material_vocabulary.json": ("TRAIN-fitted material vocabulary (valid material names / aliases); built by "
                                              "scripts/run_representation.py"),
    "data.file.category_capabilities.json": "which preferences each garment category supports; copied by scripts/run_representation.py",
    "data.error_title": "A processed data file in `{dir}` cannot be used: `{file}`.",
    "data.problem_line": "- Problem: {problem}",
    "data.error_help": ("The file is probably incomplete, corrupted or from an incompatible version. Copy a complete `data/processed/` folder "
                        "again or rebuild it (see `docs/DEMO_APP.md`, section *Required data files*). The app only reads TRAIN rows and does not "
                        "repair or regenerate data."),
    "data.problem.unreadable_parquet": "not a readable Parquet file ({error})",
    "data.problem.missing_columns": "required column(s) missing: {columns}",
    "data.problem.train_rows_unreadable": "TRAIN rows could not be read ({error})",
    "data.problem.no_train_rows": "the file contains no rows with split == 'train'",
    "data.problem.unreadable_json": "not a readable JSON file ({error})",
    "data.problem.missing_keys": "required key(s) missing: {keys}",
    "data.problem.missing_categories": "required key 'categories' missing",

    # ------------------------------------------------------------ form
    "form.header": "Your garment",
    "form.no_preference": "No preference",
    "form.no_templates_suffix": "  (no TRAIN templates)",
    "form.no_templates_warning": "There are no TRAIN garments for this segment and category, so CAGO cannot generate designs for it.",
    "form.section.materials": "Materials",
    "form.section.look": "Look",
    "form.section.functional": "Functional preferences",
    "form.functional_caption": "Composition-based proxies, not measured performance.",
    "form.help.preferred_material": "Materials seen in TRAIN garments of this category.",
    "form.help.forbidden_materials": "Hard constraint: these materials never appear in a recommendation.",
    "form.help.colour": "Colours of TRAIN templates in this cell. CAGO V1 does not recolour garments: colour is inherited from the template.",
    "form.choose_options": "Choose options",
    "form.unavailable_help": "Unavailable: {reason}.",
    "form.unavailable_list": "Unavailable for this category: {fields}.",
    "form.advanced": "Advanced",
    "form.seed": "Reproducibility seed",
    "form.templates": "Templates",
    "form.candidates_per_template": "Candidates per template",
    "form.budget_caption": ("Default budget equals the final TEST evaluation budget ({n_templates} × {per_template}). The budget is an app "
                            "setting; it does not change the frozen generator."),
    "form.generate": "Generate recommendations",
    "availability.insufficient_train_support": "not enough labelled TRAIN garments for this category",
    "availability.not_applicable": "not applicable to this garment category in CAGO V1",

    # field labels (capitalised, as in form labels) and in-sentence forms
    "field.segment": "Segment",
    "field.category": "Garment category",
    "field.preferred_material": "Preferred dominant material",
    "field.forbidden_materials": "Forbidden materials",
    "field.colour": "Colour",
    "field.fit": "Fit",
    "field.length": "Length",
    "field.stretch": "Stretch",
    "field.thermal_warmth": "Thermal warmth",
    "field.breathability": "Breathability",
    "field.durability": "Durability",
    "field.moisture_wicking": "Moisture wicking",
    "field.water_repellent": "Water repellency",
    "field.request": "request",
    "field_lc.segment": "segment",
    "field_lc.category": "garment category",
    "field_lc.preferred_material": "preferred dominant material",
    "field_lc.forbidden_materials": "forbidden materials",
    "field_lc.colour": "colour",
    "field_lc.fit": "fit",
    "field_lc.length": "length",
    "field_lc.stretch": "stretch",
    "field_lc.thermal_warmth": "thermal warmth",
    "field_lc.breathability": "breathability",
    "field_lc.durability": "durability",
    "field_lc.moisture_wicking": "moisture wicking",
    "field_lc.water_repellent": "water repellency",
    "field_lc.request": "request",
    "value.yes": "yes",

    # preference names used inside explanations (frozen intent preference ids)
    "pref.preferred_dominant_material": "preferred dominant material",
    "pref.colour": "colour",
    "pref.fit": "fit",
    "pref.length_cut": "length",
    "pref.stretch": "stretch",
    "pref.thermal_warmth": "thermal warmth",
    "pref.breathability": "breathability",
    "pref.durability_wear": "durability",
    "pref.moisture_wicking": "moisture wicking",
    "pref.water_repellent": "water repellency",

    # ------------------------------------------------------------ progress (service)
    "progress.validating": "Validating your requirements",
    "progress.generating": "Generating candidates (Generator B3)",
    "progress.evaluating": "Evaluating candidates (Intent, SR1–SR5, Plausibility) and selecting",
    "progress.done": "Done",

    # ------------------------------------------------------------ status line
    "status.generated_in": "generated in {seconds} s",
    "status.candidates": "{generated} of {requested} requested candidates",
    "status.hard_valid": "{n} hard-valid",
    "status.front": "{n} on the Pareto front",
    "status.templates": "{used} of {eligible} eligible TRAIN templates used",
    "status.seed": " · seed {seed}",

    # ------------------------------------------------------------ roles
    "role.balanced": "Balanced",
    "role.sorting_focused": "Sorting-focused",
    "role.intent_focused": "Intent-focused",
    "role.joiner": " + ",
    "role.and": " and ",
    "role.slash": " / ",
    "role.balanced_reason": ("Balanced was selected because it is closest to the ideal point among the {front_size} Pareto candidate(s), "
                             "giving equal weight to {objectives} and {last_objective} (distance {distance})."),
    "role.objective.violations": "sorting-rule violations (scaled 0–5)",
    "role.objective.intent_loss": "intent loss",
    "role.objective.plausibility_loss": "plausibility loss",
    "role.list_sep": ", ",
    "role.sorting_reason_zero": "Sorting-focused was selected because it has no detected SR1–SR5 violations{tail}.",
    "role.sorting_reason_min": ("Sorting-focused was selected because it has the lowest violation count on the Pareto front ({count}){tail}. "
                                "No Pareto candidate reached zero detected violations."),
    "role.sorting_tail_intent": ", while keeping an intent alignment of {intent}/100",
    "role.intent_reason": "Intent-focused was selected because it has the highest intent alignment on the Pareto front ({intent}/100).",

    # ------------------------------------------------------------ card
    "card.same_candidate": "The same candidate fulfils {roles}.",
    "card.summary": "**{category}** · colour: {colour} · fit: {fit} · length: {length}",
    "card.na": "n/a",
    "card.not_labelled": "not labelled",
    "card.merged_caption": "Identical materials listed in several slots of one component are merged for display.",
    "card.metric.intent": "Intent alignment",
    "card.metric.plausibility": "Plausibility",
    "card.metric.violations": "SR violations",
    "card.metric.intent_help": ("Intent Alignment (0–100): how well the candidate matches your soft preferences, estimated from the "
                                "composition and the template labels. n/a when no preference can be scored."),
    "card.metric.plausibility_help": ("Dataset-relative Plausibility (0–100): support and similarity of the composition relative to the "
                                      "TRAIN garments of this category. It is not a manufacturability measure."),
    "card.metric.violations_help": ("Number of flagged SR1–SR5 sorting-screening rules (0–5). Zero detected violations does not guarantee "
                                    "recyclability or manufacturability."),
    "card.violations_value": "{n} / 5",
    "card.why": "Why this recommendation",
    "card.your_preferences": "**Your preferences**",
    "card.preference_line": "- {preference} = `{requested}`: **{status}**. {explanation}",
    "card.technical_evidence": "Technical evidence: {text}",
    "card.sr_expander": "SR1–SR5 sorting-screening results",
    "card.sr_line": "- {icon} **{rule} · {name}**: {status}. {detail}",
    "card.changes_expander": "Changes from the TRAIN template",
    "card.template_caption": ("Template garment `{template}` · {n_subs} material substitution(s) · total absolute percentage change {abs_change} "
                              "points (summed over every material slot, so moving 2 points from one slot to another counts as 4)."),

    # ------------------------------------------------------------ preference status
    "pstatus.satisfied": "satisfied",
    "pstatus.partially_satisfied": "partially satisfied",
    "pstatus.not_satisfied": "not satisfied",
    "pstatus.not_scored": "not scored",

    # ------------------------------------------------------------ headline / comparisons
    "headline.matches_one": "Matches your {prefs} preference.",
    "headline.matches_many": "Matches your {prefs} preferences.",
    "headline.misses_one": "Does not fully meet your {prefs} preference.",
    "headline.misses_many": "Does not fully meet your {prefs} preferences.",
    "headline.retains_one": "Retains {rules} sorting-screening violation.",
    "headline.retains_many": "Retains {rules} sorting-screening violations.",
    "headline.list_sep": ", ",
    "compare.line": "Compared with the {roles} recommendation, this candidate has {parts}.",
    "compare.parts_sep": ", ",
    "compare.fewer_violations": "fewer sorting-rule violations ({a} vs {b})",
    "compare.more_violations": "more sorting-rule violations ({a} vs {b})",
    "compare.higher_intent": "higher intent alignment ({a} vs {b})",
    "compare.lower_intent": "lower intent alignment ({a} vs {b})",
    "compare.higher_plausibility": "higher dataset-relative plausibility ({a} vs {b})",
    "compare.lower_plausibility": "lower dataset-relative plausibility ({a} vs {b})",

    # ------------------------------------------------------------ score labels
    "score.not_scored": "not scored (no scorable preference)",
    "score.value": "{value} / 100",

    # ------------------------------------------------------------ SR1–SR5 (identifiers SR1..SR5 never translated)
    "sr.SR1.name": "Supported fibre composition",
    "sr.SR1.ok": "The readable (outer) composition is a mono- or two-fibre blend that the screening rules list as supported.",
    "sr.SR2.name": "Blend complexity",
    "sr.SR2.ok": "The readable composition has fewer than three distinct fibres.",
    "sr.SR3.name": "Minor-fibre detectability",
    "sr.SR3.ok": "Every non-dominant fibre of the readable composition is at least 5%.",
    "sr.SR4.name": "Colour screening",
    "sr.SR4.ok": "The garment colour is not black (black is used as a screening proxy for detection difficulty).",
    "sr.SR5.name": "Hidden-layer consistency",
    "sr.SR5.ok": "Linings / fillings do not contain a material above 5% that is absent from the surface.",
    "sr.SR1.name_lc": "supported fibre composition",
    "sr.SR2.name_lc": "blend complexity",
    "sr.SR3.name_lc": "minor-fibre detectability",
    "sr.SR4.name_lc": "colour screening",
    "sr.SR5.name_lc": "hidden-layer consistency",
    "sr.status.violated": "Violation detected",
    "sr.status.ok": "No violation detected",
    "sr.zero_violations": "No violations detected under the CAGO SR1–SR5 sorting-screening rules.",
    "sr.summary_flagged": "{count} of 5 sorting-screening rules flagged: {rules}.",
    "sr.rule_with_name": "{rule} ({name})",
    "sr.list_sep": ", ",
    "sr.sr1_detail": "Readable composition: {reason}.",
    "sr.sr1_reason.unsupported_mono": "single fibre outside the supported list",
    "sr.sr1_reason.unsupported_binary": "two-fibre blend outside the supported list",
    "sr.sr1_reason.more_than_two_fibres": "more than two fibres",
    "sr.sr1_reason.no_readable_material": "no readable material",
    "sr.sr2_detail": "Readable composition has {count} distinct fibres (3 or more is flagged).",
    "sr.sr3_detail": "Minor fibre(s) below 5%: {materials}.",
    "sr.sr3_detail_generic": "Minor fibre below 5%.",
    "sr.sr4_detail": "Colour is '{colour}'. Colour is inherited from the TRAIN template and is not changed by CAGO V1.",
    "sr.sr5_detail": "{where} contains {materials} not present on the surface.",
    "sr.sr5_hidden_layer": "hidden layer",
    "sr.material_pct": "{material} {pct}",
    "sr.material_sep": ", ",

    # ------------------------------------------------------------ preference explanations (display wording of frozen evidence)
    "share.breathable_fibre_share": "share of breathable fibres (linen, cotton, lyocell, viscose) in the main fabric",
    "share.light_fibre_share": "share of light fibres (cotton, linen, lyocell, viscose) in the main fabric",
    "share.wool_acrylic_share": "share of wool and acrylic in the main fabric",
    "share.nylon_share": "share of nylon in the main fabric",
    "share.polyester_nylon_share": "share of polyester and nylon in the main fabric",
    "share.polyester_filling_share": "share of polyester in the filling",
    "share.wool_penalty": "deduction for wool in the main fabric",
    "flag.coating_penalty": "a coating layer lowers breathability",
    "flag.filling_penalty": "a filling layer counts against this preference",
    "flag.filling_present": "a filling layer adds warmth",
    "flag.polyester_blend": "a polyester blend adds durability",
    "flag.coating_component": "a coating layer (strong water-repellency evidence)",
    "flag.supporting_synthetic_shell": "a mainly synthetic outer fabric (supporting evidence only, not proof)",
    "flag.strong_evidence_present": "strong water-repellency evidence found",
    "flag.no_strong_evidence": "no strong water-repellency evidence (a synthetic outer fabric alone is not proof)",
    "flag.neutral": "neutral request",
    "bucket.none": "no elastane (no stretch)",
    "bucket.low": "a low elastane share (low stretch)",
    "bucket.high": "a high elastane share (high stretch)",
    "bucket.out_of_range": "an elastane share outside the supported range",
    "evidence.share_pct": "{text}: {pct}",
    "evidence.share_raw": "{text}: {value}",
    "evidence.text_mentions": "product text mentions {terms}",
    "evidence.text_sep": ", ",
    "evidence.elastane": "elastane share: {value}",
    "evidence.stretch_level": "stretch level: {bucket}",
    "evidence.main_fabric": "main fabric: {component}",
    "evidence.template_label": "template label: {label}",
    "evidence.colour": "colour: {colour}",
    "unscorable.neutral_value": "'standard' is a neutral choice, so it is not scored",
    "unscorable.no_label_evidence": ("the template has no {pref} label in the dataset, so this preference cannot be checked (it is not counted "
                                     "as a miss)"),
    "unscorable.no_primary_component_materials": "the main fabric lists no materials",
    "unscorable.candidate_colour_unavailable": "the template has no recorded colour",
    "unscorable.no_evidence": "no evidence",
    "explain.not_scored": "Not scored: {why}.",
    "explain.dominant_where_named": "the main fabric ({component})",
    "explain.dominant_where": "the main fabric",
    "explain.dominant_match": "The largest material in {where} is {material} at {pct}.",
    "explain.dominant_mismatch": "The largest material in {where} is {material} at {pct}, not {requested}.",
    "explain.label_src": "inherited from the TRAIN template",
    "explain.label_src_colour": "inherited from the TRAIN template; CAGO does not recolour",
    "explain.label_value": "The {name} is '{got}' ({src}); you asked for '{requested}'.",
    "explain.bool.full": "Composition-based estimate: fully supports {name}",
    "explain.bool.none": "Composition-based estimate: does not support {name}",
    "explain.bool.partial": "Composition-based estimate: partly supports {name}",
    "explain.enum.full": "Composition-based estimate: fully meets '{value}' {name}",
    "explain.enum.none": "Composition-based estimate: does not meet '{value}' {name}",
    "explain.enum.partial": "Composition-based estimate: partly meets '{value}' {name}",
    "explain.evidence_join": " — {phrases}",
    "explain.evidence_sep": "; ",
    "explain.proxy_tail": ". This is a proxy from the material list, not a measured property.",

    # ------------------------------------------------------------ mutation / template-change descriptions
    "change.component": "{component} component",
    "change.forbidden_reason": " to remove a forbidden material",
    "change.substitution": ("Change {n}: replaced {from_material} with {to_material} in the {component} "
                            "(that material made up {pct} of it){why}."),
    "change.move_same": "Change {n}: moved {points} between two {material} entries in the {component} (the material total is unchanged).",
    "change.move": ("Change {n}: moved {points} from {from_material} to {to_material} in the {component} "
                    "({from_material} {from_before} → {from_after}, {to_material} {to_before} → {to_after})."),
    "change.points_one": "{value} percentage point",
    "change.points_many": "{value} percentage points",
    "rulechange.undo_one": "undoing change {n}",
    "rulechange.undo_many": "undoing any one of changes {first} or {last}",
    "rulechange.undo_sep": ", ",
    "rulechange.resolved": "{rule} ({name}) is no longer flagged, while the template was flagged",
    "rulechange.introduced": "{rule} ({name}) is newly flagged compared with the template",
    "rulechange.resolved_confirmed": "; confirmed: {undo} on its own brings the flag back",
    "rulechange.introduced_confirmed": "; confirmed: {undo} on its own removes the flag",
    "rulechange.unconfirmed": "; no single change alone is confirmed as the cause",
    "rulechange.end": ".",
    "tradeoff.violations": "SR1–SR5 violations: template {template} → candidate {candidate} ({delta}).",
    "tradeoff.intent": "Intent alignment: template {template} → candidate {candidate} ({delta} points).",
    "tradeoff.plausibility": "Dataset-relative plausibility: template {template} → candidate {candidate} ({delta} points).",
    "tradeoff.fewer_violations_lower_intent": ("Trade-off: sorting rule violations decreased while intent alignment decreased relative to "
                                               "the template."),
    "tradeoff.more_violations_higher_intent": ("Trade-off: intent alignment increased while sorting rule violations increased relative to "
                                               "the template."),

    # ------------------------------------------------------------ validation errors
    "error.missing_required_field": "Please choose a {label}.",
    "error.invalid_target_segment": "This segment is not available in the CAGO TRAIN data.",
    "error.invalid_detail_category": "This garment category is not available in the CAGO TRAIN data.",
    "error.unknown_material": "Unknown material: {detail}.",
    "error.invalid_value": "Invalid value for {label}: {detail}.",
    "error.removed_in_v1": "{label}: {detail}.",
    "error.unknown_field": "Unknown field: {detail}.",
    "error.generic": "{detail}",
    "error.no_preference_hint": "; choose one of these or 'No preference'",
    "error.true_only_hint": "only true or 'No preference' is allowed",
    # structured detail texts (used by the Turkish rendering; English keeps the frozen engine wording as detail)
    "error.detail.enum": "{value} is not one of {allowed}; choose one of these or 'No preference'",
    "error.detail.true_only": "{value} is not allowed: only true or 'No preference' is allowed",
    "error.detail.colour": "colour must be a non-empty string or null",
    "error.detail.forbidden_list": "must be a list of material names or null",
    "error.detail.removed_hint": "{value} was removed in V1; use {hint} (allowed: {allowed})",
    "error.detail.removed": "{value} was removed in V1 (allowed: {allowed})",
    "error.detail.invalid_request": "request must be an object",
    "error.allowed_sep": ", ",

    # ------------------------------------------------------------ warnings
    "warning.control_not_available": "{labels} is not available for this garment category, so this preference was not used.",
    "warning.hard_override": "Your preferred material is also forbidden. Forbidden materials are a hard constraint, so the preference was not used.",
    "warning.preference_conflict": ("Possible conflict between {labels}: {reason}. "
                                    "Both preferences are kept; the trade-off is visible in the results."),
    "warning.labels_sep": ", ",
    "warning.unknown": "{message}",
    "conflict.fit_stretch": "the chosen fit is rarely combined with the chosen stretch level in the dataset",
    "conflict.breathability_water_repellent": "water-repellency evidence (coatings, membranes) works against high breathability",
    "conflict.thermal_warmth_breathability": "heavy warmth (fillings, padding) works against high breathability",
    "conflict.stretch_forbidden_materials": "stretch is estimated from elastane, but elastane is forbidden",
    "conflict.moisture_wicking_forbidden_materials": "moisture wicking is estimated from polyester and nylon, but both are forbidden",
    "conflict.preferred_dominant_material_stretch": "an elastane-dominant material contradicts 'no stretch'",
    "conflict.generic": "these preferences are rarely satisfied together",

    # ------------------------------------------------------------ result messages
    "msg.no_templates": ("No recommendations can be generated because {why}. "
                         "CAGO only builds designs from TRAIN garment templates of the same segment and category."),
    "msg.no_templates.empty_cell": "there are no TRAIN garments for this segment and category",
    "msg.no_templates.unusable": "none of the {n} TRAIN garments in this cell has a clean, fully usable composition",
    "msg.no_candidates": "No candidate could be generated. {parts} Try removing a forbidden material or choosing another category.",
    "msg.no_candidates.failed": "{n} template(s) contain a forbidden material that has no TRAIN-supported replacement",
    "msg.no_candidates.rejected": "other attempts were rejected: {reasons}",
    "msg.no_candidates.rejection": "{reason} ({n})",
    "msg.no_candidates.sep": "; ",
    "msg.no_candidates.list_sep": ", ",
    "msg.no_valid": "All {n} generated candidates failed the hard validity checks, so no recommendation is shown.",
    "msg.no_zero_violation": "No candidate reached zero detected SR1–SR5 violations (lowest: {min}).{extra}",
    "msg.no_zero_violation.sr4": (" Every candidate with the lowest violation count keeps the SR4 colour flag: the colour is inherited from "
                                  "TRAIN templates and is not changed by CAGO V1."),
    "msg.single_pareto": "Only one candidate is non-dominated, so all recommendation roles point to the same design.",
    "msg.duplicate_roles": "One candidate fulfils several recommendation roles; it is shown once with all its roles.",
    "msg.no_intent.ignored": ("Your soft preference(s) ({prefs}) are not available for this garment category and were not used, "
                              "so there is no Intent-focused recommendation."),
    "msg.no_intent.none": "No soft preference was given, so there is no Intent-focused recommendation.",
    "msg.no_intent.unscorable": ("None of your soft preferences could be scored for the Pareto-front candidates ({detail}), so there is no "
                                 "Intent-focused recommendation and intent alignment is shown as n/a."),
    "msg.no_intent.detail": "{pref}: {reasons}",
    "msg.no_intent.detail_sep": "; ",
    "msg.no_intent.reason_sep": ", ",
    "msg.no_intent.list_sep": ", ",
    "unscorable_short.neutral_value": "'standard' is neutral and not scored",
    "unscorable_short.no_label_evidence": "the templates have no label for it",
    "unscorable_short.no_primary_component_materials": "no main-fabric materials",
    "unscorable_short.candidate_colour_unavailable": "no recorded colour",
    "msg.small_pool": ("Only {n} eligible TRAIN template(s) exist for this cell; "
                       "fewer and less diverse candidates are possible."),
    "msg.config_note": ("Generator B3 (proposal + repair, STRICT_SORTING) with frozen research settings; only the candidate budget and seed "
                        "are app parameters."),

    # ------------------------------------------------------------ Pareto chart
    "chart.group.front": "Pareto front",
    "chart.group.other": "Other candidates",
    "chart.axis.intent": "Intent alignment (0–100)",
    "chart.axis.violations": "SR1–SR5 violations",
    "chart.axis.plausibility": "Dataset-relative plausibility (0–100)",
    "chart.no_intent_axis": "Intent alignment is n/a for every candidate (no scorable soft preference), so the x axis shows SR1–SR5 violations instead.",
    "chart.unplotted": ("{n} candidate(s) without a scorable preference have no intent value and are not "
                        "plotted; they are listed in the candidate table."),
    "chart.tooltip.candidate": "candidate",
    "chart.tooltip.intent": "intent",
    "chart.tooltip.plausibility": "plausibility",
    "chart.tooltip.violations": "SR violations",
    "chart.tooltip.role": "recommended as",
    "chart.caption": ("Each dot is an evaluated hard-valid candidate. Numbers above Pareto-front dots are SR1–SR5 violation counts; "
                      "circled dots are the recommendations. The Pareto front uses three objectives (violations, intent, plausibility), so a grey "
                      "dot can look better in this 2-D view while having more SR1–SR5 violations."),
    "chart.table_expander": "Candidate table",
    "chart.col.candidate_id": "candidate_id",
    "chart.col.intent": "intent_0_100",
    "chart.col.plausibility": "plausibility_0_100",
    "chart.col.violations": "violation_count",
    "chart.col.is_pareto": "is_pareto",
    "chart.col.role": "role",

    # ------------------------------------------------------------ technical details
    "tech.expander": "Technical details",
    "tech.budget": ("Budget: {n_templates} templates × {per_template} candidates · seed {seed} (demo setting; it does not reproduce "
                    "the final TEST benchmark)."),
    "tech.train_only": "Generation, evaluation and support statistics use TRAIN garments only.",
    "tech.sr_rules": "**SR1–SR5 screening rules**",
    "tech.sr_rule_line": "- **{rule} · {name}**: {text}",
    "tech.request": "**Normalised request**",
    "tech.stats": "**Run statistics**",
}

# English is the source language: the vocabulary is rendered from the internal identifiers (see translator.py).
VOCAB: dict[str, dict[str, str]] = {}
