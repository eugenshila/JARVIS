from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LauncherTests(unittest.TestCase):
    def test_windows_launcher_marks_direct_main_invocation_as_cli(self):
        launcher = (ROOT / "scripts" / "start_jarvis.bat").read_text(encoding="utf-8")

        cli_environment = 'set "JARVIS_CLI=1"'
        direct_launch = "python main.py"
        self.assertIn(cli_environment, launcher)
        self.assertIn(direct_launch, launcher)
        self.assertLess(launcher.index(cli_environment), launcher.index(direct_launch))


if __name__ == "__main__":
    unittest.main()
