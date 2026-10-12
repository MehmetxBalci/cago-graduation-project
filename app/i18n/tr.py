"""Turkish UI catalog (Türkçe arayüz metinleri).

Same keys and placeholders as `en.py` (tested). `VOCAB` holds the display labels of internal identifiers; the identifiers
themselves (material, colour, category, fit, length, ... values) are never changed and are the only values passed to the
research engine. Where a domain term has no reliable Turkish equivalent, the label keeps the original identifier
(e.g. `elastomultiester`, `lyocell`, polymer abbreviations) instead of inventing a meaning; these are listed in `RETAINED`.

Terminology (see docs/LOCALIZATION.md): Intent Alignment = Tercihlere Uyum, Dataset-relative Plausibility = Veri Setine Göre
Gerçekçilik, Balanced = Dengeli, Sorting-focused = Ayıklama Odaklı, Intent-focused = Tercih Odaklı, sorting-screening rule
violation = Ayıklama Tarama Kuralı İhlali. SR1–SR5 identifiers are never translated.
"""
from __future__ import annotations

LANGUAGE_NAME = "Türkçe"

MESSAGES: dict[str, str] = {
    # ------------------------------------------------------------ sayfa / başlık
    "app.page_title": "CAGO demo",
    "app.title": "CAGO",
    "app.subtitle": ("**Constraint-Aware Garment Optimization (Kısıt Farkındalıklı Giysi Optimizasyonu)** · Giysi gereksinimlerinizi seçin; "
                     "CAGO gerçek TRAIN (eğitim verisi) giysi şablonlarını bu gereksinimlere uyarlar ve her adayı SR1–SR5 tekstil ayıklama "
                     "kurallarıyla tarar."),
    "app.prototype_notice": "Prototip uyarısı · ",
    "app.loading_data": "TRAIN şablonları ve destek tabloları yükleniyor ...",
    "app.language_label": "Dil",
    "app.language_help": ("Arayüz dilini değiştirir. Yalnızca metinler değişir: istek, üretilen adaylar ve tüm puanlar aynı kalır."),
    "app.start_hint": "Kenar çubuğunda gereksinimlerinizi seçin ve **Önerileri üret** düğmesine basın.",
    "app.stale_results": "Bu sonuçlar üretildikten sonra ayarlar değişti. Sonuçları güncellemek için **Önerileri üret** düğmesine basın.",
    "app.pareto_header": "Pareto adaylarına genel bakış",
    "app.progress_start": "Başlatılıyor ...",

    # ------------------------------------------------------------ uyarı metni
    "disclaimer.1": "CAGO bir bitirme projesi prototipidir.",
    "disclaimer.2": "Ayıklama sonuçları yalnızca SR1–SR5 tarama kurallarını ifade eder.",
    "disclaimer.3": "Hiç ihlal tespit edilmemesi geri dönüştürülebilirliği veya üretilebilirliği garanti etmez.",
    "disclaimer.4": "Gerçekçilik veri setine görelidir: TRAIN veri setine göre destek ve benzerliği ölçer.",
    "disclaimer.5": "Öneriler, TRAIN veri setinde bulunan örüntülerden ve destekten üretilir.",

    # ------------------------------------------------------------ veri dosyası ekranları
    "data.missing_title": "Gerekli işlenmiş veri dosyaları `{dir}` klasöründe eksik.",
    "data.missing_help": ("`docs/DEMO_APP.md` belgesine bakın (*Required data files* bölümü). Uygulamayı `CAGO_PROCESSED_DIR` ortam "
                          "değişkeniyle başka bir klasöre yönlendirebilirsiniz."),
    "data.file.garment_representation.parquet": ("TRAIN giysi şablonları (bileşen bileşimleri, etiketler, split sütunu); "
                                                 "scripts/run_representation.py ile oluşturulur"),
    "data.file.ml_material_vocabulary.json": ("TRAIN verisinden çıkarılan malzeme sözlüğü (geçerli malzeme adları / eş anlamlılar); "
                                              "scripts/run_representation.py ile oluşturulur"),
    "data.file.category_capabilities.json": ("her giysi kategorisinin hangi tercihleri desteklediği; scripts/run_representation.py ile "
                                             "kopyalanır"),
    "data.error_title": "`{dir}` içindeki işlenmiş bir veri dosyası kullanılamıyor: `{file}`.",
    "data.problem_line": "- Sorun: {problem}",
    "data.error_help": ("Dosya büyük olasılıkla eksik, bozuk ya da uyumsuz bir sürüme ait. Eksiksiz bir `data/processed/` klasörünü yeniden "
                        "kopyalayın veya yeniden oluşturun (`docs/DEMO_APP.md`, *Required data files* bölümü). Uygulama yalnızca TRAIN "
                        "satırlarını okur; veriyi onarmaz ve yeniden üretmez."),
    "data.problem.unreadable_parquet": "okunabilir bir Parquet dosyası değil ({error})",
    "data.problem.missing_columns": "gerekli sütun(lar) eksik: {columns}",
    "data.problem.train_rows_unreadable": "TRAIN satırları okunamadı ({error})",
    "data.problem.no_train_rows": "dosyada split == 'train' olan satır yok",
    "data.problem.unreadable_json": "okunabilir bir JSON dosyası değil ({error})",
    "data.problem.missing_keys": "gerekli anahtar(lar) eksik: {keys}",
    "data.problem.missing_categories": "gerekli 'categories' anahtarı eksik",

    # ------------------------------------------------------------ form
    "form.header": "Giysiniz",
    "form.no_preference": "Tercih yok",
    "form.help.category": "Yalnızca seçilen hedef grupta en az bir uygun TRAIN giysi şablonu bulunan kategoriler listelenir.",
    "form.no_categories": "Bu hedef grup için uygun TRAIN şablonu olan hiçbir giysi kategorisi yok; bu nedenle CAGO bu seçim için tasarım üretemez. Başka bir hedef grup seçin.",
    "form.invalid_combination": "Seçilen hedef grup ve giysi kategorisi için uygun TRAIN şablonu yok; bu nedenle hiçbir şey üretilmedi. Listeden bir kategori seçin.",
    "app.stale_request": "Aşağıdaki sonuçlar önceki isteğe aittir: {request}.",
    "request.item": "{label}: {value}",
    "request.sep": " · ",
    "request.list_sep": ", ",
    "form.section.materials": "Malzemeler",
    "form.section.look": "Görünüm",
    "form.section.functional": "Fonksiyonel tercihler",
    "form.functional_caption": "Bileşime dayalı yaklaşık göstergelerdir; ölçülmüş performans değildir.",
    "form.help.preferred_material": "Bu kategorideki TRAIN giysilerinde görülen malzemeler.",
    "form.help.forbidden_materials": "Zorunlu kısıt: bu malzemeler hiçbir öneride yer almaz.",
    "form.help.colour": ("Bu hücredeki TRAIN şablonlarının renkleri. CAGO V1 giysileri yeniden renklendirmez: renk şablondan devralınır. "
                         "Renk adları veri setindeki ürün renklerinden gelir; güvenilir bir Türkçe karşılığı olmayan kısımlar (ör. desen "
                         "veya karakter adları) orijinal haliyle gösterilir."),
    "form.choose_options": "Malzeme seçin",
    "form.unavailable_help": "Kullanılamıyor: {reason}.",
    "form.unavailable_list": "Bu kategori için kullanılamayanlar: {fields}.",
    "form.advanced": "Gelişmiş",
    "form.seed": "Tekrarlanabilirlik tohumu (seed)",
    "form.templates": "Şablon sayısı",
    "form.candidates_per_template": "Şablon başına aday",
    "form.budget_caption": ("Varsayılan bütçe, final TEST değerlendirmesinin bütçesine eşittir ({n_templates} × {per_template}). Bütçe bir "
                            "uygulama ayarıdır; donmuş üreticiyi değiştirmez."),
    "form.generate": "Önerileri üret",
    "availability.insufficient_train_support": "bu kategori için yeterli sayıda etiketli TRAIN giysisi yok",
    "availability.not_applicable": "CAGO V1'de bu giysi kategorisi için geçerli değil",

    "field.segment": "Hedef grup",
    "field.category": "Giysi kategorisi",
    "field.preferred_material": "Tercih edilen baskın malzeme",
    "field.forbidden_materials": "Yasaklı malzemeler",
    "field.colour": "Renk",
    "field.fit": "Kesim",
    "field.length": "Boy",
    "field.stretch": "Esneme",
    "field.thermal_warmth": "Sıcak tutma",
    "field.breathability": "Nefes alabilirlik",
    "field.durability": "Dayanıklılık",
    "field.moisture_wicking": "Nem uzaklaştırma",
    "field.water_repellent": "Su iticilik",
    "field.request": "istek",
    "field_lc.segment": "hedef grup",
    "field_lc.category": "giysi kategorisi",
    "field_lc.preferred_material": "tercih edilen baskın malzeme",
    "field_lc.forbidden_materials": "yasaklı malzemeler",
    "field_lc.colour": "renk",
    "field_lc.fit": "kesim",
    "field_lc.length": "boy",
    "field_lc.stretch": "esneme",
    "field_lc.thermal_warmth": "sıcak tutma",
    "field_lc.breathability": "nefes alabilirlik",
    "field_lc.durability": "dayanıklılık",
    "field_lc.moisture_wicking": "nem uzaklaştırma",
    "field_lc.water_repellent": "su iticilik",
    "field_lc.request": "istek",
    "value.yes": "evet",

    "pref.preferred_dominant_material": "tercih edilen baskın malzeme",
    "pref.colour": "renk",
    "pref.fit": "kesim",
    "pref.length_cut": "boy",
    "pref.stretch": "esneme",
    "pref.thermal_warmth": "sıcak tutma",
    "pref.breathability": "nefes alabilirlik",
    "pref.durability_wear": "dayanıklılık",
    "pref.moisture_wicking": "nem uzaklaştırma",
    "pref.water_repellent": "su iticilik",

    # ------------------------------------------------------------ ilerleme
    "progress.validating": "Gereksinimleriniz doğrulanıyor",
    "progress.generating": "Adaylar üretiliyor (Generator B3)",
    "progress.evaluating": "Adaylar değerlendiriliyor (Tercihlere Uyum, SR1–SR5, Gerçekçilik) ve seçim yapılıyor",
    "progress.done": "Tamamlandı",

    # ------------------------------------------------------------ durum satırı
    "status.generated_in": "{seconds} sn içinde üretildi",
    "status.candidates": "istenen {requested} adaydan {generated} tanesi üretildi",
    "status.hard_valid": "{n} aday zorunlu kısıtları sağlıyor",
    "status.front": "{n} aday Pareto cephesinde",
    "status.templates": "{eligible} uygun TRAIN şablonundan {used} tanesi kullanıldı",
    "status.seed": " · tohum {seed}",

    # ------------------------------------------------------------ roller
    "role.balanced": "Dengeli",
    "role.sorting_focused": "Ayıklama Odaklı",
    "role.intent_focused": "Tercih Odaklı",
    "role.joiner": " + ",
    "role.and": " ve ",
    "role.slash": " / ",
    "role.balanced_reason": ("Dengeli öneri, {front_size} Pareto adayı arasında ideal noktaya en yakın aday olduğu için seçildi; "
                             "{objectives} ve {last_objective} eşit ağırlıkla dikkate alındı (uzaklık {distance})."),
    "role.objective.violations": "ayıklama kuralı ihlalleri (0–5 ölçeğinde)",
    "role.objective.intent_loss": "tercih kaybı",
    "role.objective.plausibility_loss": "gerçekçilik kaybı",
    "role.list_sep": ", ",
    "role.sorting_reason_zero": "Ayıklama Odaklı öneri, tespit edilmiş hiçbir SR1–SR5 ihlali olmadığı için seçildi{tail}.",
    "role.sorting_reason_min": ("Ayıklama Odaklı öneri, Pareto cephesindeki en düşük ihlal sayısına ({count}) sahip olduğu için seçildi{tail}. "
                                "Hiçbir Pareto adayı sıfır tespit edilmiş ihlale ulaşamadı."),
    "role.sorting_tail_intent": "; Tercihlere Uyum puanı {intent}/100 düzeyinde korunuyor",
    "role.intent_reason": ("Tercih Odaklı öneri, Pareto cephesindeki en yüksek Tercihlere Uyum puanına ({intent}/100) sahip olduğu için "
                           "seçildi."),

    # ------------------------------------------------------------ kart
    "card.same_candidate": "Aynı aday şu rolleri üstleniyor: {roles}.",
    "card.summary": "**{category}** · renk: {colour} · kesim: {fit} · boy: {length}",
    "card.na": "yok",
    "card.not_labelled": "etiketsiz",
    "card.merged_caption": "Bir bileşenin birden fazla yuvasında listelenen aynı malzemeler, gösterim için birleştirilmiştir.",
    "card.metric.intent": "Tercihlere Uyum",
    "card.metric.plausibility": "Gerçekçilik",
    "card.metric.violations": "SR ihlalleri",
    "card.metric.intent_help": ("Tercihlere Uyum (0–100): adayın esnek tercihlerinize ne kadar uyduğu; bileşimden ve şablon etiketlerinden "
                                "tahmin edilir. Hiçbir tercih puanlanamıyorsa 'yok' gösterilir."),
    "card.metric.plausibility_help": ("Veri Setine Göre Gerçekçilik (0–100): bileşimin bu kategorideki TRAIN giysilerine göre desteği ve "
                                      "benzerliği. Bir üretilebilirlik ölçüsü değildir."),
    "card.metric.violations_help": ("İşaretlenen SR1–SR5 ayıklama tarama kuralı sayısı (0–5). Hiç ihlal tespit edilmemesi geri "
                                    "dönüştürülebilirliği veya üretilebilirliği garanti etmez."),
    "card.violations_value": "{n} / 5",
    "card.why": "Bu öneri neden seçildi",
    "card.your_preferences": "**Tercihleriniz**",
    "card.preference_line": "- {preference} = `{requested}`: **{status}**. {explanation}",
    "card.technical_evidence": "Teknik kanıt (donmuş değerlendirme çıktısı, özgün İngilizce metin): {text}",
    "card.sr_expander": "SR1–SR5 ayıklama tarama sonuçları",
    "card.sr_line": "- {icon} **{rule} · {name}**: {status}. {detail}",
    "card.changes_expander": "TRAIN şablonuna göre değişiklikler",
    "card.template_caption": ("Şablon giysi `{template}` · {n_subs} malzeme ikamesi · toplam mutlak yüzde değişimi {abs_change} puan "
                              "(tüm malzeme yuvaları üzerinden toplanır; bu nedenle bir yuvadan diğerine 2 puan aktarmak 4 sayılır)."),

    # ------------------------------------------------------------ tercih durumu
    "pstatus.satisfied": "karşılandı",
    "pstatus.partially_satisfied": "kısmen karşılandı",
    "pstatus.not_satisfied": "karşılanmadı",
    "pstatus.not_scored": "puanlanmadı",

    # ------------------------------------------------------------ özet / karşılaştırma
    "headline.matches_one": "Şu tercihinize uyuyor: {prefs}.",
    "headline.matches_many": "Şu tercihlerinize uyuyor: {prefs}.",
    "headline.misses_one": "Şu tercihinizi tam olarak karşılamıyor: {prefs}.",
    "headline.misses_many": "Şu tercihlerinizi tam olarak karşılamıyor: {prefs}.",
    "headline.retains_one": "Ayıklama tarama kuralı ihlali devam ediyor: {rules}.",
    "headline.retains_many": "Ayıklama tarama kuralı ihlalleri devam ediyor: {rules}.",
    "headline.list_sep": ", ",
    "compare.line": "{roles} önerisine kıyasla bu aday: {parts}.",
    "compare.parts_sep": ", ",
    "compare.fewer_violations": "daha az ayıklama kuralı ihlali (bu aday {a}, diğeri {b})",
    "compare.more_violations": "daha fazla ayıklama kuralı ihlali (bu aday {a}, diğeri {b})",
    "compare.higher_intent": "daha yüksek Tercihlere Uyum (bu aday {a}, diğeri {b})",
    "compare.lower_intent": "daha düşük Tercihlere Uyum (bu aday {a}, diğeri {b})",
    "compare.higher_plausibility": "daha yüksek Veri Setine Göre Gerçekçilik (bu aday {a}, diğeri {b})",
    "compare.lower_plausibility": "daha düşük Veri Setine Göre Gerçekçilik (bu aday {a}, diğeri {b})",

    "score.not_scored": "puanlanmadı (puanlanabilir tercih yok)",
    "score.value": "{value} / 100",

    # ------------------------------------------------------------ SR1–SR5 (SR kimlikleri çevrilmez)
    "sr.SR1.name": "Desteklenen lif bileşimi",
    "sr.SR1.ok": ("Okunabilir (dış) bileşim, tarama kurallarında desteklenen olarak listelenen tek lifli ya da iki lifli bir karışımdır."),
    "sr.SR2.name": "Karışım karmaşıklığı",
    "sr.SR2.ok": "Okunabilir bileşimde üçten az farklı lif vardır.",
    "sr.SR3.name": "Düşük oranlı lif saptanabilirliği",
    "sr.SR3.ok": "Okunabilir bileşimdeki baskın olmayan her lifin payı en az %5'tir.",
    "sr.SR4.name": "Renk taraması",
    "sr.SR4.ok": "Giysi rengi siyah değildir (siyah, saptama güçlüğü için tarama göstergesi olarak kullanılır).",
    "sr.SR5.name": "Gizli katman tutarlılığı",
    "sr.SR5.ok": "Astar / dolgu katmanlarında, yüzeyde bulunmayan ve payı %5'in üzerinde olan bir malzeme yoktur.",
    "sr.SR1.name_lc": "desteklenen lif bileşimi",
    "sr.SR2.name_lc": "karışım karmaşıklığı",
    "sr.SR3.name_lc": "düşük oranlı lif saptanabilirliği",
    "sr.SR4.name_lc": "renk taraması",
    "sr.SR5.name_lc": "gizli katman tutarlılığı",
    "sr.status.violated": "İhlal tespit edildi",
    "sr.status.ok": "İhlal tespit edilmedi",
    "sr.zero_violations": "CAGO SR1–SR5 ayıklama tarama kurallarına göre ihlal tespit edilmedi.",
    "sr.summary_flagged": "5 ayıklama tarama kuralından {count} tanesi işaretlendi: {rules}.",
    "sr.rule_with_name": "{rule} ({name})",
    "sr.list_sep": ", ",
    "sr.sr1_detail": "Okunabilir bileşim: {reason}.",
    "sr.sr1_reason.unsupported_mono": "desteklenen listenin dışında tek bir lif",
    "sr.sr1_reason.unsupported_binary": "desteklenen listenin dışında iki lifli bir karışım",
    "sr.sr1_reason.more_than_two_fibres": "ikiden fazla lif",
    "sr.sr1_reason.no_readable_material": "okunabilir malzeme yok",
    "sr.sr2_detail": "Okunabilir bileşimde {count} farklı lif var (3 veya daha fazlası işaretlenir).",
    "sr.sr3_detail": "Payı %5'in altında olan düşük oranlı lif(ler): {materials}.",
    "sr.sr3_detail_generic": "Payı %5'in altında olan düşük oranlı lif.",
    "sr.sr4_detail": "Renk: '{colour}'. Renk TRAIN şablonundan devralınır ve CAGO V1 tarafından değiştirilmez.",
    "sr.sr5_detail": "Katman: {where} — yüzeyde bulunmayan malzeme içeriyor: {materials}.",
    "sr.sr5_hidden_layer": "gizli katman",
    "sr.material_pct": "{material} {pct}",
    "sr.material_sep": ", ",

    # ------------------------------------------------------------ tercih açıklamaları
    "share.breathable_fibre_share": "ana kumaştaki nefes alabilen liflerin (keten, pamuk, lyocell, viskon) payı",
    "share.light_fibre_share": "ana kumaştaki hafif liflerin (pamuk, keten, lyocell, viskon) payı",
    "share.wool_acrylic_share": "ana kumaştaki yün ve akrilik payı",
    "share.nylon_share": "ana kumaştaki naylon payı",
    "share.polyester_nylon_share": "ana kumaştaki polyester ve naylon payı",
    "share.polyester_filling_share": "dolgudaki polyester payı",
    "share.wool_penalty": "ana kumaştaki yün için uygulanan kesinti",
    "flag.coating_penalty": "bir kaplama katmanı nefes alabilirliği düşürür",
    "flag.filling_penalty": "bir dolgu katmanı bu tercihin aleyhine sayılır",
    "flag.filling_present": "bir dolgu katmanı sıcak tutmayı artırır",
    "flag.polyester_blend": "bir polyester karışımı dayanıklılığı artırır",
    "flag.coating_component": "bir kaplama katmanı (güçlü su iticilik kanıtı)",
    "flag.supporting_synthetic_shell": "ağırlıklı olarak sentetik bir dış kumaş (yalnızca destekleyici kanıt, kesin kanıt değil)",
    "flag.strong_evidence_present": "güçlü su iticilik kanıtı bulundu",
    "flag.no_strong_evidence": "güçlü su iticilik kanıtı yok (sentetik bir dış kumaş tek başına kanıt değildir)",
    "flag.neutral": "nötr istek",
    "bucket.none": "elastan yok (esneme yok)",
    "bucket.low": "düşük elastan payı (düşük esneme)",
    "bucket.high": "yüksek elastan payı (yüksek esneme)",
    "bucket.out_of_range": "desteklenen aralığın dışında bir elastan payı",
    "evidence.share_pct": "{text}: {pct}",
    "evidence.share_raw": "{text}: {value}",
    "evidence.text_mentions": "ürün metninde geçen ifadeler: {terms}",
    "evidence.text_sep": ", ",
    "evidence.elastane": "elastan payı: {value}",
    "evidence.stretch_level": "esneme düzeyi: {bucket}",
    "evidence.main_fabric": "ana kumaş: {component}",
    "evidence.template_label": "şablon etiketi: {label}",
    "evidence.colour": "renk: {colour}",
    "unscorable.neutral_value": "'standart' nötr bir seçimdir, bu nedenle puanlanmaz",
    "unscorable.no_label_evidence": ("şablonun veri setinde {pref} etiketi yok; bu nedenle bu tercih kontrol edilemez (karşılanmamış "
                                     "sayılmaz)"),
    "unscorable.no_primary_component_materials": "ana kumaşta malzeme listelenmemiş",
    "unscorable.candidate_colour_unavailable": "şablonun kayıtlı bir rengi yok",
    "unscorable.no_evidence": "kanıt yok",
    "explain.not_scored": "Puanlanmadı: {why}.",
    "explain.dominant_where_named": "ana kumaş: {component}",
    "explain.dominant_where": "ana kumaş",
    "explain.dominant_match": "En büyük paya sahip malzeme ({where}): {material}, {pct}.",
    "explain.dominant_mismatch": "En büyük paya sahip malzeme ({where}): {material}, {pct}; istenen malzeme ({requested}) değil.",
    "explain.label_src": "TRAIN şablonundan devralındı",
    "explain.label_src_colour": "TRAIN şablonundan devralındı; CAGO rengi değiştirmez",
    "explain.label_value": "Bu adayın {name} değeri '{got}' ({src}); sizin isteğiniz '{requested}'.",
    "explain.bool.full": "Bileşime dayalı tahmin: {name} özelliğini tam olarak destekliyor",
    "explain.bool.none": "Bileşime dayalı tahmin: {name} özelliğini desteklemiyor",
    "explain.bool.partial": "Bileşime dayalı tahmin: {name} özelliğini kısmen destekliyor",
    "explain.enum.full": "Bileşime dayalı tahmin: '{value}' {name} isteğini tam olarak karşılıyor",
    "explain.enum.none": "Bileşime dayalı tahmin: '{value}' {name} isteğini karşılamıyor",
    "explain.enum.partial": "Bileşime dayalı tahmin: '{value}' {name} isteğini kısmen karşılıyor",
    "explain.evidence_join": " — {phrases}",
    "explain.evidence_sep": "; ",
    "explain.proxy_tail": ". Bu, ölçülmüş bir özellik değil, malzeme listesinden elde edilen yaklaşık bir göstergedir.",

    # ------------------------------------------------------------ değişiklik açıklamaları
    "change.component": "{component} bileşeni",
    "change.forbidden_reason": " — yasaklı bir malzemeyi çıkarmak için",
    "change.substitution": ("Değişiklik {n}: {component} içinde {from_material} yerine {to_material} kullanıldı "
                            "(bu malzeme bileşenin {pct} kadarını oluşturuyordu){why}."),
    "change.move_same": ("Değişiklik {n}: {component} içindeki iki {material} girdisi arasında {points} aktarıldı "
                         "(malzemenin toplam payı değişmedi)."),
    "change.move": ("Değişiklik {n}: {component} içinde {from_material} malzemesinden {to_material} malzemesine {points} aktarıldı "
                    "({from_material} {from_before} → {from_after}, {to_material} {to_before} → {to_after})."),
    "change.points_one": "{value} yüzde puan",
    "change.points_many": "{value} yüzde puan",
    "rulechange.undo_one": "{n} numaralı değişikliğin geri alınması",
    "rulechange.undo_many": "{first} veya {last} numaralı değişikliklerden herhangi birinin geri alınması",
    "rulechange.undo_sep": ", ",
    "rulechange.resolved": "{rule} ({name}) artık işaretlenmiyor; şablonda işaretliydi",
    "rulechange.introduced": "{rule} ({name}) şablona kıyasla yeni işaretlendi",
    "rulechange.resolved_confirmed": "; doğrulandı: tek başına {undo} işareti geri getiriyor",
    "rulechange.introduced_confirmed": "; doğrulandı: tek başına {undo} işareti kaldırıyor",
    "rulechange.unconfirmed": "; neden olarak tek başına hiçbir değişiklik doğrulanmadı",
    "rulechange.end": ".",
    "tradeoff.violations": "SR1–SR5 ihlalleri: şablon {template} → aday {candidate} ({delta}).",
    "tradeoff.intent": "Tercihlere Uyum: şablon {template} → aday {candidate} ({delta} puan).",
    "tradeoff.plausibility": "Veri Setine Göre Gerçekçilik: şablon {template} → aday {candidate} ({delta} puan).",
    "tradeoff.fewer_violations_lower_intent": ("Ödünleşim: şablona kıyasla ayıklama kuralı ihlalleri azalırken Tercihlere Uyum da "
                                               "düştü."),
    "tradeoff.more_violations_higher_intent": ("Ödünleşim: şablona kıyasla Tercihlere Uyum artarken ayıklama kuralı ihlalleri de arttı."),

    # ------------------------------------------------------------ doğrulama hataları
    "error.missing_required_field": "Lütfen bir {label} seçin.",
    "error.invalid_target_segment": "Bu hedef grup CAGO TRAIN verisinde mevcut değil.",
    "error.invalid_detail_category": "Bu giysi kategorisi CAGO TRAIN verisinde mevcut değil.",
    "error.unknown_material": "Bilinmeyen malzeme: {detail}.",
    "error.invalid_value": "{label} için geçersiz değer: {detail}.",
    "error.removed_in_v1": "{label}: {detail}.",
    "error.unknown_field": "Bilinmeyen alan: {detail}.",
    "error.generic": "{detail}",
    "error.no_preference_hint": "; bunlardan birini ya da 'Tercih yok' seçeneğini seçin",
    "error.true_only_hint": "yalnızca evet ya da 'Tercih yok' seçilebilir",
    "error.detail.enum": "{value} şu seçeneklerden biri değil: {allowed}; bunlardan birini ya da 'Tercih yok' seçeneğini seçin",
    "error.detail.true_only": "{value} kabul edilmiyor: yalnızca evet ya da 'Tercih yok' seçilebilir",
    "error.detail.colour": "renk boş olmayan bir metin olmalı ya da boş bırakılmalı",
    "error.detail.forbidden_list": "malzeme adlarından oluşan bir liste olmalı ya da boş bırakılmalı",
    "error.detail.removed_hint": "{value} V1'de kaldırıldı; bunun yerine {hint} kullanın (izin verilenler: {allowed})",
    "error.detail.removed": "{value} V1'de kaldırıldı (izin verilenler: {allowed})",
    "error.detail.invalid_request": "istek bir nesne (sözlük) olmalı",
    "error.allowed_sep": ", ",

    # ------------------------------------------------------------ uyarılar
    "warning.control_not_available": "{labels} bu giysi kategorisi için kullanılamıyor; bu nedenle bu tercih dikkate alınmadı.",
    "warning.hard_override": ("Tercih ettiğiniz malzeme aynı zamanda yasaklı. Yasaklı malzemeler zorunlu bir kısıttır; bu nedenle tercih "
                              "dikkate alınmadı."),
    "warning.preference_conflict": ("Olası tercih çatışması ({labels}): {reason}. "
                                    "İki tercih de korunur; aradaki ödünleşim sonuçlarda görülebilir."),
    "warning.labels_sep": ", ",
    "warning.unknown": "{message}",
    "conflict.fit_stretch": "seçilen kesim, veri setinde seçilen esneme düzeyiyle nadiren birlikte görülür",
    "conflict.breathability_water_repellent": "su iticilik kanıtı (kaplamalar, membranlar) yüksek nefes alabilirliğe ters etki eder",
    "conflict.thermal_warmth_breathability": "yüksek sıcak tutma (dolgular, vatka) yüksek nefes alabilirliğe ters etki eder",
    "conflict.stretch_forbidden_materials": "esneme elastan payından tahmin edilir, ancak elastan yasaklandı",
    "conflict.moisture_wicking_forbidden_materials": "nem uzaklaştırma polyester ve naylon payından tahmin edilir, ancak ikisi de yasaklandı",
    "conflict.preferred_dominant_material_stretch": "elastanın baskın olduğu bir malzeme 'esneme yok' tercihiyle çelişir",
    "conflict.generic": "bu tercihler nadiren birlikte karşılanır",

    # ------------------------------------------------------------ sonuç mesajları
    "msg.no_templates": ("Öneri üretilemiyor, çünkü {why}. "
                         "CAGO tasarımları yalnızca aynı hedef grup ve kategorideki TRAIN giysi şablonlarından oluşturur."),
    "msg.no_templates.empty_cell": "bu hedef grup ve kategori için TRAIN giysisi yok",
    "msg.no_templates.unusable": "bu hücredeki {n} TRAIN giysisinin hiçbirinin temiz ve tam kullanılabilir bir bileşimi yok",
    "msg.no_candidates": ("Hiç aday üretilemedi. {parts} Yasaklı bir malzemeyi kaldırmayı ya da başka bir kategori seçmeyi deneyin."),
    "msg.no_candidates.failed": "{n} şablon, TRAIN verisinde desteklenen bir ikamesi olmayan yasaklı bir malzeme içeriyor",
    "msg.no_candidates.rejected": "diğer denemeler reddedildi: {reasons}",
    "msg.no_candidates.rejection": "{reason} ({n})",
    "msg.no_candidates.sep": "; ",
    "msg.no_candidates.list_sep": ", ",
    "msg.no_valid": "Üretilen {n} adayın tamamı zorunlu geçerlilik kontrollerinden geçemedi; bu nedenle öneri gösterilmiyor.",
    "msg.no_zero_violation": "Hiçbir aday sıfır tespit edilmiş SR1–SR5 ihlaline ulaşamadı (en düşük: {min}).{extra}",
    "msg.no_zero_violation.sr4": (" En düşük ihlal sayısına sahip tüm adaylarda SR4 renk işareti kalıyor: renk TRAIN şablonlarından "
                                  "devralınır ve CAGO V1 tarafından değiştirilmez."),
    "msg.single_pareto": ("Yalnızca bir aday baskılanmamış (non-dominated) durumda; bu nedenle tüm öneri rolleri aynı tasarımı gösteriyor."),
    "msg.duplicate_roles": "Bir aday birden fazla öneri rolünü üstleniyor; tüm rolleriyle birlikte bir kez gösteriliyor.",
    "msg.no_intent.ignored": ("Esnek tercihleriniz ({prefs}) bu giysi kategorisi için kullanılamıyor ve dikkate alınmadı; bu nedenle "
                              "Tercih Odaklı öneri yok."),
    "msg.no_intent.none": "Hiç esnek tercih belirtilmedi; bu nedenle Tercih Odaklı öneri yok.",
    "msg.no_intent.unscorable": ("Esnek tercihlerinizin hiçbiri Pareto cephesindeki adaylar için puanlanamadı ({detail}); bu nedenle "
                                 "Tercih Odaklı öneri yok ve Tercihlere Uyum 'yok' olarak gösteriliyor."),
    "msg.no_intent.detail": "{pref}: {reasons}",
    "msg.no_intent.detail_sep": "; ",
    "msg.no_intent.reason_sep": ", ",
    "msg.no_intent.list_sep": ", ",
    "unscorable_short.neutral_value": "'standart' nötrdür ve puanlanmaz",
    "unscorable_short.no_label_evidence": "şablonlarda bu özellik için etiket yok",
    "unscorable_short.no_primary_component_materials": "ana kumaşta malzeme yok",
    "unscorable_short.candidate_colour_unavailable": "kayıtlı renk yok",
    "msg.small_pool": ("Bu hücre için yalnızca {n} uygun TRAIN şablonu var; daha az sayıda ve daha az çeşitli aday üretilebilir."),
    "msg.config_note": ("Donmuş araştırma ayarlarıyla Generator B3 (öneri + onarım, STRICT_SORTING); yalnızca aday bütçesi ve tohum değeri "
                        "uygulama parametresidir."),

    # ------------------------------------------------------------ Pareto grafiği
    "chart.group.front": "Pareto cephesi",
    "chart.group.other": "Diğer adaylar",
    "chart.axis.intent": "Tercihlere Uyum (0–100)",
    "chart.axis.violations": "SR1–SR5 ihlalleri",
    "chart.axis.plausibility": "Veri Setine Göre Gerçekçilik (0–100)",
    "chart.no_intent_axis": ("Hiçbir aday için Tercihlere Uyum hesaplanamadı (puanlanabilir esnek tercih yok); bu nedenle x ekseni "
                             "bunun yerine SR1–SR5 ihlallerini gösteriyor."),
    "chart.unplotted": ("Puanlanabilir tercihi olmayan {n} adayın Tercihlere Uyum değeri yok ve grafikte gösterilmiyor; bu adaylar "
                        "aday tablosunda listeleniyor."),
    "chart.tooltip.candidate": "aday",
    "chart.tooltip.intent": "tercihlere uyum",
    "chart.tooltip.plausibility": "gerçekçilik",
    "chart.tooltip.violations": "SR ihlalleri",
    "chart.tooltip.role": "önerildiği rol",
    "chart.caption": ("Her nokta, zorunlu kısıtları sağlayan ve değerlendirilmiş bir adaydır. Pareto cephesindeki noktaların üzerindeki "
                      "sayılar SR1–SR5 ihlal sayılarıdır; halka içine alınmış noktalar önerilerdir. Pareto cephesi üç amaç (ihlaller, "
                      "tercihlere uyum, gerçekçilik) kullanır; bu nedenle gri bir nokta bu 2 boyutlu görünümde daha iyi görünse de daha "
                      "fazla SR1–SR5 ihlaline sahip olabilir."),
    "chart.table_expander": "Aday tablosu",
    "chart.col.candidate_id": "Aday",
    "chart.col.intent": "Tercihlere Uyum (0–100)",
    "chart.col.plausibility": "Gerçekçilik (0–100)",
    "chart.col.violations": "SR ihlalleri",
    "chart.col.is_pareto": "Pareto cephesinde",
    "chart.col.role": "Rol",

    # ------------------------------------------------------------ teknik ayrıntılar
    "tech.expander": "Teknik ayrıntılar",
    "tech.budget": ("Bütçe: {n_templates} şablon × {per_template} aday · tohum {seed} (demo ayarı; final TEST karşılaştırmasını yeniden "
                    "üretmez)."),
    "tech.train_only": "Üretim, değerlendirme ve destek istatistikleri yalnızca TRAIN giysilerini kullanır.",
    "tech.sr_rules": "**SR1–SR5 tarama kuralları**",
    "tech.sr_rule_line": "- **{rule} · {name}**: {text}",
    "tech.request": "**Normalleştirilmiş istek** (araştırma motoruna giden iç tanımlayıcılar; çevrilmez)",
    "tech.stats": "**Çalıştırma istatistikleri**",
}

# ---------------------------------------------------------------- display labels of internal identifiers
VOCAB: dict[str, dict[str, str]] = {
    "segment": {"women": "Kadın", "men": "Erkek", "kids": "Çocuk", "baby": "Bebek"},
    "category": {
        "bras_lingerie": "Sütyen ve iç giyim", "dresses": "Elbise", "jeans": "Kot pantolon", "joggers": "Jogger (eşofman altı)",
        "jumpsuits_overalls": "Tulum", "leggings": "Tayt", "outerwear_coat": "Dış giyim – kaban / palto",
        "outerwear_gilet": "Dış giyim – yelek", "outerwear_jacket": "Dış giyim – ceket / mont", "set": "Takım",
        "shirt_blouse": "Gömlek ve bluz", "shorts": "Şort", "skirts": "Etek", "sleepwear_homewear": "Pijama ve ev giyimi",
        "socks_hosiery": "Çorap ve külotlu çorap", "sweater_cardigan": "Kazak ve hırka", "sweatshirt_hoodie": "Sweatshirt ve kapüşonlu",
        "swimwear": "Mayo ve plaj giyimi", "tank_camisole_vest": "Atlet ve askılı üst", "top_generic": "Üst (genel)",
        "trousers": "Pantolon", "tshirt_polo": "Tişört ve polo", "underwear_bottoms": "İç çamaşırı (alt)",
    },
    "material": {
        # TRAIN vocabulary tokens
        "polyester": "polyester", "cotton": "pamuk", "elastane": "elastan", "nylon": "naylon (poliamid)", "viscose": "viskon",
        "wool": "yün", "acrylic": "akrilik", "linen": "keten", "lyocell": "lyocell", "elastomultiester": "elastomultiester",
        "modal": "modal", "cashmere": "kaşmir", "metallised_fibre": "metalize lif", "polyurethane": "poliüretan",
        "mohair": "tiftik (mohair)", "alpaca": "alpaka", "cupro": "kupro", "silk": "ipek", "leather": "deri", "acetate": "asetat",
        "down": "kuş tüyü (down)", "feather": "tüy (feather)", "OTHER": "diğer", "PAD": "PAD",
        # other canonical names of the vocabulary (mapped to OTHER for ML, but valid in requests)
        "abs": "ABS", "brass": "pirinç (metal)", "cellulose": "selüloz", "copper": "bakır", "elastodiene": "elastodien", "eva": "EVA",
        "glass": "cam", "hemp": "kenevir", "iron": "demir", "jute": "jüt", "latex": "lateks", "mabs": "MABS", "metal": "metal",
        "modacrylic": "modakrilik", "paper": "kâğıt", "pbt": "PBT", "pctg": "PCTG", "pearl": "inci", "pmma": "PMMA",
        "polycarbonate": "polikarbonat", "polyethylene": "polietilen", "polypropylene": "polipropilen", "polystyrene": "polistiren",
        "pom": "POM", "ptfe": "PTFE", "ramie": "rami", "resin": "reçine", "rubber": "kauçuk", "silicone": "silikon", "steel": "çelik",
        "suede": "süet", "textile": "tekstil", "tpe": "TPE", "tpu": "TPU", "triacetate": "triasetat",
        "unspecified_material": "belirtilmemiş malzeme", "wax": "mum", "zinc": "çinko",
    },
    "fit": {"slim": "Dar kesim", "regular": "Normal kesim", "relaxed": "Rahat kesim", "oversized": "Oversize (bol kesim)"},
    "length_cut": {"standard": "Standart boy", "long": "Uzun boy", "cropped": "Kısa (crop) boy"},
    "stretch": {"none": "Esneme yok", "low": "Düşük", "high": "Yüksek"},
    "thermal_warmth": {"light": "Hafif", "standard": "Standart", "heavy": "Yüksek"},
    "breathability": {"standard": "Standart", "high": "Yüksek"},
    "durability_wear": {"standard": "Standart", "reinforced": "Güçlendirilmiş"},
    "component": {
        "application": "aplike", "back_panel": "arka panel", "base_fabric": "temel kumaş", "belt": "kemer", "binder_part": "bağlama parçası",
        "binding": "biye", "body": "gövde", "body_filling": "gövde dolgusu", "body_lining": "gövde astarı", "bottom_panel": "alt panel",
        "chest_pocket_fabric": "göğüs cebi kumaşı", "coating": "kaplama", "collar": "yaka", "crotch": "ağ (kasık) parçası", "cuff": "manşet",
        "cup_lining": "kap astarı", "decorating_thread": "süsleme ipliği", "details": "detaylar", "elastic": "lastik",
        "elastic ribs": "elastik ribana", "elastic section": "elastik bölüm", "elastic_part": "elastik parça", "embroidery": "nakış",
        "face": "yüz kumaşı", "faux_fur": "suni kürk", "filling": "dolgu", "flock_part": "flok parça", "frill": "fırfır",
        "fringe": "saçak", "front_panel": "ön panel", "hem": "etek ucu", "hood": "kapüşon", "hood_edge": "kapüşon kenarı",
        "hood_lining": "kapüşon astarı", "inner_layer": "iç katman", "inner_pants": "iç pantolon", "inner_support": "iç destek",
        "inside_panel": "iç panel", "interlining": "tela", "knit_part": "örme parça", "lace": "dantel", "lining": "astar",
        "lower": "alt kısım", "main": "ana kumaş", "mesh": "file", "middle layer": "orta katman", "net": "file (ağ)", "other": "diğer",
        "other fabric": "diğer kumaş", "outer_layer": "dış katman", "padding": "vatka", "panel": "panel", "patch_pocket": "yama cep",
        "pattern_area": "desen alanı", "petticoat": "iç etek", "piping": "kordon biye", "pocket": "cep", "pocket_fabric": "cep kumaşı",
        "pocket_lining": "cep astarı", "rib": "ribana", "shell": "dış kumaş", "side_panel": "yan panel", "skirt": "etek",
        "skirt_lining": "etek astarı", "sleeve": "kol", "sleeve_lining": "kol astarı", "sleeves": "kollar", "sock": "çorap",
        "storage_bag": "saklama torbası", "strap": "askı", "tape": "bant", "top_panel": "üst panel", "trim": "garnitür", "tulle": "tül",
        "upper": "üst kısım", "upper_body_filling": "üst gövde dolgusu", "under_body_filling": "alt gövde dolgusu",
        "upper_part": "üst parça", "waist": "bel", "wing": "kanat", "woven_part": "dokuma parça", "component": "bileşen",
    },
    "component_class": {
        "decoration": "süsleme", "filling": "dolgu", "lining": "astar", "other": "diğer", "panel": "panel", "pocket": "cep",
        "surface": "yüzey", "trim": "garnitür",
    },
    "rejection": {
        "unrepairable_forbidden_material": "onarılamayan yasaklı malzeme", "no_applicable_mutation": "uygulanabilir değişiklik yok",
        "topology_changed": "bileşen yapısı değişti", "identical_to_template": "şablonla aynı", "duplicate_candidate": "yinelenen aday",
        "gave_up_after_max_attempts": "azami deneme sayısına ulaşıldı",
        "hard_validation:forbidden_material_present": "zorunlu doğrulama: yasaklı malzeme var",
        "hard_validation:invalid_percentage": "zorunlu doğrulama: geçersiz yüzde",
        "hard_validation:negative_percentage": "zorunlu doğrulama: negatif yüzde",
        "hard_validation:non_physical_token": "zorunlu doğrulama: fiziksel olmayan malzeme belirteci",
        "hard_validation:percentage_sum_out_of_tolerance": "zorunlu doğrulama: yüzde toplamı tolerans dışında",
        "hard_validation:unknown_component_class": "zorunlu doğrulama: bilinmeyen bileşen sınıfı",
        "hard_validation:unknown_component_name": "zorunlu doğrulama: bilinmeyen bileşen adı",
        "hard_validation:unknown_material": "zorunlu doğrulama: bilinmeyen malzeme",
    },
    "text_tag": {
        "brushed": "şardonlu", "fleece": "polar", "padded": "dolgulu", "thermal": "termal", "reinforced": "güçlendirilmiş",
        "durable": "dayanıklı", "ripstop": "ripstop (yırtılmaya dayanıklı dokuma)", "heavyweight": "ağır gramajlı",
        "double_layer": "çift katlı", "quick_dry": "hızlı kuruyan", "moisture_wicking": "nem uzaklaştırıcı",
        "water_resistant": "suya dayanıklı", "membrane": "membran", "lamination": "laminasyon",
    },
}

# Identifiers deliberately shown unchanged in Turkish (no reliable Turkish term; trade names / abbreviations / proper nouns).
RETAINED = {
    "material": {"polyester", "lyocell", "elastomultiester", "modal", "metal", "PAD"},
    "component": {"panel", "brown: navy", "green"},
    "component_class": {"panel"},
}

# ---------------------------------------------------------------- colours
# Dataset colours are free retail colour names ("light beige/leopard print", "black/spider-man"). They are translated
# phrase-by-phrase: every segment separated by "/" or " - " is translated only when ALL its words are known; otherwise
# the segment is kept in its original form (pattern, licence or character names have no reliable translation).
COLOUR_PHRASES: dict[str, str] = {
    "off white": "kırık beyaz", "navy blue": "lacivert", "steel blue": "çelik mavisi", "old rose": "gül kurusu",
    "powder pink": "pudra pembe", "dusty pink": "gül kurusu", "denim blue": "denim mavisi", "leopard print": "leopar desenli",
    "animal print": "hayvan desenli", "khaki green": "haki yeşil", "olive green": "zeytin yeşili", "bottle green": "şişe yeşili",
    "sky blue": "gök mavisi", "royal blue": "saks mavisi", "dark red": "koyu kırmızı", "light grey marl": "açık gri melanj",
    "multi colour": "çok renkli", "multi color": "çok renkli",
}
COLOUR_WORDS: dict[str, str] = {
    "black": "siyah", "white": "beyaz", "grey": "gri", "gray": "gri", "beige": "bej", "blue": "mavi", "navy": "lacivert",
    "pink": "pembe", "brown": "kahverengi", "cream": "krem", "green": "yeşil", "yellow": "sarı", "red": "kırmızı", "purple": "mor",
    "lilac": "lila", "orange": "turuncu", "turquoise": "turkuaz", "khaki": "haki", "olive": "zeytin yeşili", "ecru": "ekru",
    "burgundy": "bordo", "silver": "gümüş", "gold": "altın", "camel": "deve tüyü", "mint": "mint yeşili", "coral": "mercan",
    "mustard": "hardal", "anthracite": "antrasit", "charcoal": "kömür grisi", "taupe": "vizon", "sand": "kum", "stone": "taş",
    "lavender": "lavanta", "plum": "mürdüm", "indigo": "çivit mavisi", "aqua": "su yeşili", "rose": "gül", "nude": "ten rengi",
    "natural": "doğal", "transparent": "şeffaf", "multicolour": "çok renkli", "multicolor": "çok renkli", "denim": "denim",
    "light": "açık", "dark": "koyu", "medium": "orta", "pale": "soluk", "bright": "parlak", "dusty": "soluk", "warm": "sıcak",
    "neon": "neon", "vintage": "eskitme", "washed": "yıkanmış", "marl": "melanj", "marle": "melanj", "melange": "melanj",
    "striped": "çizgili", "stripe": "çizgili", "stripes": "çizgili", "pinstripe": "ince çizgili", "checked": "kareli",
    "check": "kareli", "patterned": "desenli", "pattern": "desenli", "floral": "çiçekli", "dotted": "puantiyeli",
    "spotted": "benekli", "leopard": "leopar", "zebra": "zebra", "camouflage": "kamuflaj",
}
