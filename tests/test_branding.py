"""P85: the Unformat brand is the default; the build's copies match branding/unformat/."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "branding/unformat"
PUBLIC = ROOT / "erpnext_drive_integrations/public"


class Branding(unittest.TestCase):
    def test_brand_file_is_complete(self):
        brand = json.loads((BRAND / "brand.json").read_text())
        self.assertEqual(brand["name"], "Unformat")
        for key in ("website_title", "website_name", "logo", "favicons", "colours"):
            self.assertIn(key, brand)
        for name in [brand["logo"]] + brand["favicons"]:
            self.assertTrue((BRAND / name).is_file(), name)
        for colour in brand["colours"].values():
            self.assertRegex(colour, r"^#[0-9A-Fa-f]{6}$")

    def test_build_copies_are_the_unformat_files(self):
        brand = json.loads((BRAND / "brand.json").read_text())
        self.assertEqual((PUBLIC / "company-logo-approved-v6.svg").read_bytes(), (BRAND / brand["logo"]).read_bytes())
        for name in brand["favicons"]:
            self.assertEqual((PUBLIC / ("company-" + name)).read_bytes(), (BRAND / name).read_bytes(), name)

    def test_pngs_carry_no_metadata_chunks(self):
        for path in BRAND.glob("*.png"):
            data, i, kinds = path.read_bytes(), 8, set()
            while i < len(data):
                length = int.from_bytes(data[i:i + 4], "big")
                kinds.add(data[i + 4:i + 8])
                i += 12 + length
            self.assertFalse(kinds & {b"eXIf", b"tEXt", b"iTXt", b"zTXt"}, path.name)

    def test_front_page_defaults_to_the_brand_name(self):
        source = (ROOT / "tools/prepare_runtime.py").read_text()
        self.assertIn("text('website_title', BRAND['website_title'])", source)
        self.assertIn("text('website_name', BRAND['website_name'])", source)

    def test_guide_and_trademark_note(self):
        guide = (ROOT / "branding/README.md").read_text()
        self.assertIn("company_logo", guide)
        self.assertIn("company_favicon_dir", guide)
        self.assertIn("trademarks of **unformat.in**", guide)
        for name in ("README.md", "LICENSES.md"):
            text = (ROOT / name).read_text()
            self.assertIn("Copyright © 2026 unformat.in", text, name)
            self.assertNotIn("and contributors", text.split("Copyright ©", 1)[1][:80], name)


if __name__ == "__main__":
    unittest.main()
