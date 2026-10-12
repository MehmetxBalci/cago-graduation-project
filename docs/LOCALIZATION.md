# CAGO V1.1 — bilingual interface (English / Turkish)

The Streamlit demo app can be used in **English** (default) or **Turkish**. Localization is **presentation only**: it never changes the
request passed to the research engine, the generated candidates, any score, the SR1–SR5 flags, the Pareto front or the selected
recommendation roles. The frozen research package (`cago/`), `scripts/`, `tests/`, the final TEST configuration and all recorded
results are unchanged (verified by hash, see [V1_1_RELEASE_NOTES.md](V1_1_RELEASE_NOTES.md)).

## Switching the language

* The **EN / TR** switcher is in the upper-right corner of the page. English is selected when the app starts.
* Switching keeps every selection (segment, category, materials, colour, fit, length, functional preferences, seed and budget).
* Switching does **not** run the generator again. Recommendations that were already generated stay on screen and are re-rendered in
  the selected language: the status line (including the generation time), the result digest in *Technical details* and the
  candidate IDs remain identical. Changing the language never marks results as stale.
* Generation only runs when **Generate recommendations / Önerileri üret** is pressed.

## Architecture

```
app/i18n/
  en.py          English catalog: MESSAGES {key: template}; source language (V1.0.0 wording, tested against a golden file)
  tr.py          Turkish catalog: same keys and placeholders; VOCAB display labels; RETAINED identifiers; colour word lists
  translator.py  Translator: t(key, **params), label(domain, id), option_labels(...), to_internal(...), number formatting
  __init__.py    get_translator("en" | "tr"), DEFAULT_LANGUAGE = "en"
```

* **Stable keys.** Every user-facing string has a dotted key (`form.generate`, `role.balanced`, `sr.SR4.name`, `msg.no_templates`, …).
  No module contains paired Turkish/English conditionals; code calls `tr.t(key, **params)`.
* **Safe interpolation.** Templates use `{name}` placeholders. A placeholder without a value raises `TranslationError` (never renders
  `{name}`). Both catalogs must use the same placeholders per key (tested).
* **Missing keys.** With `CAGO_I18N_STRICT=1` (used for the test runs) a missing key raises. Without it the translator falls back to
  English **and records** the key in `Translator.missing` plus a log warning — it is never silent. The tests guarantee identical key
  sets, so the fallback is not reachable in a released build.
* **Display ↔ internal mapping.** Widgets keep the **internal identifiers** as their options (`cotton`, `relaxed`, `black`,
  `trousers`, …) and only format them with `format_func`. `Translator.option_labels(domain, values)` gives a unique, reversible label per
  value (colliding labels get the identifier appended, e.g. `Gri (grey)` / `Gri (gray)`), `Translator.to_internal(domain, label, values)`
  maps back. Translated labels are therefore never sent to the frozen functions (tested by spying on the generator and evaluator).
* **Rendering a stored result.** `app/service.py` runs validation → B3 → evaluation once. The result keeps the structured inputs of the
  wording (`render_data`: Oracle outputs, intent entries, mutation log, rule changes, trade-offs, message arguments). `render_result`
  writes every text in one language; `localize_result(result, lang)` returns a re-rendered copy without calling the generator or the
  evaluator. `research_view(result)` extracts the language-independent part used for the EN/TR equivalence tests.
* **Streamlit state.** The language lives in `st.session_state["cago_lang"]`. All inputs have stable keys. Because Streamlit matches a
  widget value by its *displayed* label, the language switch callback re-asserts each input's internal value so it survives the label
  change. The input panel is no longer an `st.form`, so every selection is committed immediately and can always be preserved.
* **Frozen engine text.** The *Technical evidence* line under each preference is the frozen evaluation's own explanation and stays in
  its original English in both languages (labelled as such in Turkish). Frozen validation and trade-off sentences are parsed from their
  structured values and re-worded, never modified.
* **Numbers.** Turkish uses a decimal comma and a leading percent sign (`%2,5`, `0,601`, `2,0 sn`); English output is unchanged.

### Adding or changing a string

1. Add the key to `app/i18n/en.py` and `app/i18n/tr.py` (same placeholders).
2. Use it with `tr.t("your.key", name=value)`.
3. Run `CAGO_I18N_STRICT=1 python -m pytest app/tests -q`; `test_i18n.py` fails on a missing key, a placeholder mismatch, a key used in
   code but absent from the catalogs, or an untranslated Turkish string.

### V1.2 additions

Segment-aware category filtering adds `form.help.category`, `form.no_categories` (segment without available categories),
`form.invalid_combination` (defensive guard), `app.stale_request` and `request.*` (names the request an outdated result belongs to).
The V1.1 keys `form.no_templates_suffix` / `form.no_templates_warning` were removed because no category is shown with
"(no TRAIN templates)" any more. Category labels are translated with the existing `category` vocabulary (all 23 categories); the
selectors keep the internal identifiers, so switching the language never changes the selected segment / category.

## Glossary (EN → TR)

| English | Türkçe | Note |
|---|---|---|
| Intent Alignment | Tercihlere Uyum | 0–100 index; "n/a" → "yok" |
| Dataset-relative Plausibility | Veri Setine Göre Gerçekçilik | short metric label: Gerçekçilik |
| Balanced | Dengeli | recommendation role |
| Sorting-focused | Ayıklama Odaklı | recommendation role |
| Intent-focused | Tercih Odaklı | recommendation role |
| sorting-screening rule violation | Ayıklama Tarama Kuralı İhlali | |
| SR1–SR5 | SR1–SR5 | identifiers never translated |
| No violations detected under the CAGO SR1–SR5 sorting-screening rules | CAGO SR1–SR5 ayıklama tarama kurallarına göre ihlal tespit edilmedi | not a recyclability claim |
| Supported fibre composition / Blend complexity / Minor-fibre detectability / Colour screening / Hidden-layer consistency | Desteklenen lif bileşimi / Karışım karmaşıklığı / Düşük oranlı lif saptanabilirliği / Renk taraması / Gizli katman tutarlılığı | SR1 … SR5 names |
| Pareto front | Pareto cephesi | |
| candidate | aday | |
| template (TRAIN template) | şablon (TRAIN şablonu) | TRAIN = eğitim verisi; the split name is kept |
| hard-valid | zorunlu kısıtları sağlayan | |
| hard constraint | zorunlu kısıt | |
| soft preference | esnek tercih | |
| forbidden material | yasaklı malzeme | |
| preferred dominant material | tercih edilen baskın malzeme | |
| segment (women / men / kids / baby) | hedef grup (Kadın / Erkek / Çocuk / Bebek) | |
| garment category | giysi kategorisi | e.g. trousers → Pantolon, shorts → Şort |
| eligible TRAIN template | uygun TRAIN şablonu | V1.2 category availability |
| The results below belong to the previous request | Aşağıdaki sonuçlar önceki isteğe aittir | outdated results |
| fit: slim / regular / relaxed / oversized | kesim: Dar kesim / Normal kesim / Rahat kesim / Oversize (bol kesim) | |
| length: standard / long | boy: Standart boy / Uzun boy | |
| stretch, thermal warmth, breathability, durability, moisture wicking, water repellency | esneme, sıcak tutma, nefes alabilirlik, dayanıklılık, nem uzaklaştırma, su iticilik | composition-based proxies |
| cotton, linen, wool, silk, viscose, elastane, nylon | pamuk, keten, yün, ipek, viskon, elastan, naylon (poliamid) | |
| polyester, lyocell, modal, elastomultiester | polyester, lyocell, modal, elastomultiester | kept: no distinct Turkish term |
| main fabric / shell / lining / filling | ana kumaş / dış kumaş / astar / dolgu | component names |
| black, white, navy blue, off white, grey marl | siyah, beyaz, lacivert, kırık beyaz, gri melanj | colours |
| recyclability / manufacturability | geri dönüştürülebilirlik / üretilebilirlik | only in the disclaimer ("garanti etmez") |
| seed | tohum (seed) | |
| Technical evidence | Teknik kanıt | frozen English text shown verbatim |

## Translation policy for domain identifiers

* Every material of the TRAIN vocabulary and every canonical material name, all 23 garment categories, the 4 segments, all fit, length
  and functional-preference values, all component names and classes, generator rejection reasons and text-evidence tags have a Turkish
  label (tested against the read-only source vocabulary files).
* Where no reliable Turkish term exists, the identifier is shown unchanged and listed in `tr.RETAINED` (e.g. `elastomultiester`,
  `lyocell`, polymer abbreviations such as `ABS`, `PCTG`). No meaning is invented.
* Colours are free retail names in the dataset (`light beige/leopard print`, `black/spider-man`). Each part separated by `/` or ` - ` is
  translated only if all its words are known colour/pattern words; other parts (character, licence or fantasy names such as
  `spider-man`, `mole`) are shown as in the data. The colour help text explains this.
* Source vocabulary files and the processed data are never modified.
