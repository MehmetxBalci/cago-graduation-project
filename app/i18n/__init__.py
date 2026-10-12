"""Bilingual (English / Turkish) presentation layer of the CAGO demo app. Presentation only: nothing here is passed to
the frozen research engine. See docs/LOCALIZATION.md."""
from app.i18n.translator import (DEFAULT_LANGUAGE, EN, LANGUAGE_BUTTONS, SUPPORTED_LANGUAGES, TranslationError, Translator,  # noqa: F401
                                 get_translator)
