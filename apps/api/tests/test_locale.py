"""Tests for locale handling."""

from app.core.locale import DEFAULT_LOCALE, get_locale, normalize_locale, set_locale


class TestNormalizeLocale:
    def test_chinese_variants(self):
        assert normalize_locale("zh-CN") == "zh"
        assert normalize_locale("zh-TW") == "zh"
        assert normalize_locale("zh") == "zh"

    def test_english_variants(self):
        assert normalize_locale("en-US") == "en"
        assert normalize_locale("en-GB") == "en"
        assert normalize_locale("en") == "en"

    def test_japanese(self):
        assert normalize_locale("ja-JP") == "ja"
        assert normalize_locale("ja") == "ja"

    def test_unsupported_falls_back(self):
        assert normalize_locale("fr") == DEFAULT_LOCALE
        assert normalize_locale("de-DE") == DEFAULT_LOCALE
        assert normalize_locale("ko") == DEFAULT_LOCALE

    def test_empty_and_whitespace(self):
        assert normalize_locale("") == DEFAULT_LOCALE
        assert normalize_locale("  ") == DEFAULT_LOCALE

    def test_underscore_separator(self):
        assert normalize_locale("zh_CN") == "zh"
        assert normalize_locale("en_US") == "en"

    def test_case_insensitive(self):
        assert normalize_locale("ZH-CN") == "zh"
        assert normalize_locale("EN") == "en"


class TestContextVar:
    def test_default_locale(self):
        assert get_locale() == DEFAULT_LOCALE

    def test_set_and_get(self):
        set_locale("zh")
        assert get_locale() == "zh"
        # Reset
        set_locale(DEFAULT_LOCALE)
