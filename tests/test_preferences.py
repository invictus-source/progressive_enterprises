import unittest

import config


class FontPreferenceTests(unittest.TestCase):
    def test_legacy_multiplier_uses_normal_font_size(self):
        self.assertEqual(config.normalize_font_size(1.0), 10)

    def test_font_size_is_clamped_to_desktop_safe_range(self):
        self.assertEqual(config.normalize_font_size(3), 9)
        self.assertEqual(config.normalize_font_size(99), 18)

    def test_invalid_font_size_uses_default(self):
        self.assertEqual(config.normalize_font_size("invalid"), 10)


if __name__ == "__main__":
    unittest.main()
