"""App-launch tests: importing ``coinkitty_wallet.app`` and starting the app.

The app is single-instance on its D-Bus session, so the launch test always
gets its own private bus (``dbus-run-session``) and a fresh ``XDG_DATA_HOME``,
and it stops the whole process group before returning.
"""

import importlib
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import xml.etree.ElementTree

SRC_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
)
BUS_CONF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "isolated-bus.conf")


class AppImportTest(unittest.TestCase):
    def test_import_module(self):
        """``importlib.import_module`` finds the app module (catches bad relative imports)."""
        module = importlib.import_module("coinkitty_wallet.app")
        self.assertTrue(hasattr(module, "WalletApp"))

    def test_subprocess_import(self):
        """A fresh interpreter with PYTHONPATH=src imports the app with exit code 0."""
        env = dict(os.environ, PYTHONPATH=SRC_DIR)
        proc = subprocess.run(
            [sys.executable, "-c", "import coinkitty_wallet.app"],
            env=env,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0)


class AppLaunchTest(unittest.TestCase):
    def test_bus_conf_has_no_servicedirs(self):
        """The isolated bus config declares no service dirs, so nothing auto-starts on it."""
        tree = xml.etree.ElementTree.parse(BUS_CONF)
        for element in tree.iter():
            self.assertNotIn(element.tag, ("servicedir", "standard_session_servicedirs"))

    def test_launch_creates_wallet_file(self):
        """The app starts on a private bus, keeps running, and writes its demo file."""
        if shutil.which("dbus-run-session") is None or shutil.which("xvfb-run") is None:
            raise unittest.SkipTest("dbus-run-session or xvfb-run unavailable")

        tmp = tempfile.mkdtemp(prefix="coinkitty-launch-")
        env = dict(os.environ)
        env["PYTHONPATH"] = SRC_DIR
        env["XDG_DATA_HOME"] = tmp
        cmd = [
            "dbus-run-session",
            "--config-file",
            BUS_CONF,
            "--",
            "xvfb-run",
            "-a",
            sys.executable,
            "-m",
            "coinkitty_wallet",
        ]
        proc = subprocess.Popen(
            cmd,
            env=env,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        try:
            expected = os.path.join(tmp, "coinkitty-wallet", "demo-wallet.json")
            appeared = False
            deadline = time.monotonic() + 10.0
            while time.monotonic() < deadline:
                if os.path.exists(expected):
                    appeared = True
                    break
                time.sleep(0.25)
            if proc.poll() is not None:
                self.fail(
                    f"app exited early (rc={proc.returncode}); "
                    f"stderr={proc.stderr.read().decode()[-2000:]}"
                )
            self.assertTrue(appeared)
            self.assertIsNone(proc.poll())
        finally:
            try:
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait(timeout=10)
            if proc.stderr:
                proc.stderr.close()
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
