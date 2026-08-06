from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class InstallerSafetyTests(unittest.TestCase):
    def test_windows_build_references_existing_spec(self):
        build_script = (ROOT / "build_installer.ps1").read_text(encoding="utf-8")
        self.assertTrue((ROOT / "Progressive Enterprises.spec").is_file())
        self.assertIn('"Progressive Enterprises.spec"', build_script)
        self.assertIn("self_test_error.log", build_script)

    def test_installer_has_no_business_data_delete_rule(self):
        installer = (ROOT / "progressive.iss").read_text(encoding="utf-8").lower()
        self.assertNotIn("[uninstalldelete]", installer)
        for live_file in ("progressive.db", "settings.json", "prefs.json", "launcher.json"):
            self.assertNotIn(live_file, installer)

    def test_package_does_not_embed_secrets_or_live_data(self):
        spec = (ROOT / "Progressive Enterprises.spec").read_text(encoding="utf-8").lower()
        for forbidden in (".env", "progressive.db", "settings.json", "prefs.json"):
            self.assertNotIn(forbidden, spec)
        self.assertIn('"assets"', spec)

    def test_installer_is_stable_per_user_upgrade(self):
        installer = (ROOT / "progressive.iss").read_text(encoding="utf-8").lower()
        self.assertIn("appid={{", installer)
        self.assertIn("privilegesrequired=lowest", installer)
        self.assertIn("usepreviousappdir=yes", installer)

    def test_installer_shortcuts_use_embedded_executable_icon(self):
        installer = (ROOT / "progressive.iss").read_text(encoding="utf-8").lower()
        self.assertIn("uninstalldisplayicon={app}\\{#myappexename}", installer)
        self.assertNotIn("{app}\\assets\\logo.ico", installer)


if __name__ == "__main__":
    unittest.main()
