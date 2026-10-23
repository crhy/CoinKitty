import os
import shutil
import subprocess
import unittest
import xml.etree.ElementTree as ElementTree

MANIFEST = "io.github.crhy.CoinKittyWallet.yml"
DESKTOP = "data/io.github.crhy.CoinKittyWallet.desktop"
METAINFO = "data/io.github.crhy.CoinKittyWallet.metainfo.xml"
SVG = "data/io.github.crhy.CoinKittyWallet.svg"
LAUNCHER = "data/coinkitty-wallet.sh"


try:
    import yaml
except ImportError:
    yaml = None


def _load_manifest():
    """Parse the flatpak manifest with PyYAML (skips the test if absent)."""
    if yaml is None:
        raise unittest.SkipTest("no yaml module")
    with open(MANIFEST) as handle:
        return yaml.safe_load(handle)


class PackagingTest(unittest.TestCase):
    def test_manifest_declares_app(self):
        manifest = _load_manifest()
        self.assertEqual(manifest["id"], "io.github.crhy.CoinKittyWallet")
        self.assertEqual(manifest["runtime"], "org.gnome.Platform")
        self.assertEqual(manifest["runtime-version"], "50")
        self.assertEqual(manifest["sdk"], "org.gnome.Sdk")
        self.assertEqual(manifest["command"], "coinkitty-wallet")
        finish = manifest["finish-args"]
        self.assertEqual(
            finish,
            ["--share=ipc", "--socket=fallback-x11", "--socket=wayland", "--device=dri"],
        )
        for arg in finish:
            self.assertNotIn("--share=network", arg)
            self.assertNotIn("--filesystem", arg)

    def test_manifest_has_one_simple_module(self):
        manifest = _load_manifest()
        modules = manifest["modules"]
        self.assertEqual(len(modules), 1)
        module = modules[0]
        self.assertEqual(module["name"], "coinkitty-wallet")
        self.assertEqual(module["buildsystem"], "simple")
        self.assertEqual(
            module["sources"],
            [
                {"type": "dir", "path": "src/coinkitty_wallet", "dest": "coinkitty_wallet"},
                {"type": "dir", "path": "data", "dest": "data"},
            ],
        )

    def test_every_installed_data_file_exists(self):
        manifest = _load_manifest()
        for module in manifest["modules"]:
            for command in module.get("build-commands", []):
                for token in command.split():
                    if token.startswith("data/"):
                        self.assertTrue(os.path.exists(token), f"missing {token}")

    def test_launcher_is_a_sh_script(self):
        with open(LAUNCHER) as handle:
            first_line = handle.readline().rstrip("\n")
        self.assertEqual(first_line, "#!/bin/sh")
        with open(MANIFEST) as handle:
            self.assertIn("coinkitty-wallet.sh", handle.read())

    def test_desktop_file_valid(self):
        if shutil.which("desktop-file-validate") is None:
            self.skipTest("desktop-file-validate missing")
        result = subprocess.run(
            ["desktop-file-validate", DESKTOP], capture_output=True, timeout=30
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_metainfo_valid(self):
        if shutil.which("appstreamcli") is None:
            self.skipTest("appstreamcli missing")
        result = subprocess.run(
            ["appstreamcli", "validate", "--no-net", METAINFO],
            capture_output=True,
            timeout=30,
        )
        output = result.stdout.decode() + result.stderr.decode()
        for line in output.splitlines():
            self.assertNotIn("E:", line)

    def test_svg_parses(self):
        tree = ElementTree.parse(SVG)
        self.assertTrue(tree.getroot().tag.endswith("svg"))


if __name__ == "__main__":
    unittest.main()
