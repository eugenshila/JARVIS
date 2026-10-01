import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

import ui


class _NoSecrets:
    def get(self, _key):
        return None


class FocusSupportUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings_file = Path(self.temp_dir.name) / "settings.json"
        self.settings_patch = patch.object(ui, "UI_SETTINGS_FILE", self.settings_file)
        self.settings_patch.start()
        ui.ThemeManager.set_theme("calm_mint")

    def tearDown(self):
        self.settings_patch.stop()
        self.temp_dir.cleanup()

    def _board(self, **overrides):
        preferences = dict(ui.FOCUS_SUPPORT_DEFAULTS)
        preferences.update({"setup_completed": True, **overrides})
        board = ui.HybridMissionBoard(support_settings=preferences)
        board.show()
        self.app.processEvents()
        self.addCleanup(board.deleteLater)
        return board

    def test_focus_preferences_never_expose_more_than_three_primary_choices(self):
        self.settings_file.write_text(
            json.dumps({"unrelated": "preserved", "focus_support": {"max_choices": 9}}),
            encoding="utf-8",
        )
        values = ui.get_focus_support_settings()
        self.assertEqual(values["max_choices"], 3)

        saved = ui.set_focus_support_settings({"max_choices": 2, "focus_minutes": 15})
        self.assertEqual(saved["max_choices"], 2)
        persisted = json.loads(self.settings_file.read_text(encoding="utf-8"))
        self.assertEqual(persisted["unrelated"], "preserved")

    def test_guided_setup_is_opt_in_and_not_now_does_not_nag(self):
        overlay = ui.FocusSupportSetupOverlay(current=ui.FOCUS_SUPPORT_DEFAULTS)
        captured = []
        overlay.finished.connect(captured.append)
        overlay._skip()
        self.assertEqual(len(captured), 1)
        self.assertFalse(captured[0]["enabled"])
        self.assertTrue(captured[0]["setup_completed"])
        overlay.deleteLater()

    def test_settings_support_page_emits_bounded_live_preferences(self):
        overlay = ui.SettingsOverlay(focus_support={**ui.FOCUS_SUPPORT_DEFAULTS, "max_choices": 3})
        captured = []
        overlay.focus_support_changed.connect(captured.append)
        overlay._s_max_choices.setValue(3)
        overlay._s_focus_minutes.setValue(15)
        overlay._s_save_support.click()
        self.assertEqual(captured[0]["max_choices"], 3)
        self.assertEqual(captured[0]["focus_minutes"], 15)
        self.assertTrue(captured[0]["setup_completed"])
        overlay.deleteLater()

    def test_board_enforces_one_now_mission_and_restores_continuity(self):
        board = self._board()
        first = board.add_mission("Prepare the release notes", "now")
        second = board.add_mission("Review the launch checklist", "now")

        self.assertEqual([item["id"] for item in board._missions["now"]], [second["id"]])
        self.assertIn(first["id"], [item["id"] for item in board._missions["next"]])
        self.assertIn("Review the launch checklist", board._continuity)

        restored = ui.HybridMissionBoard(support_settings=board._support)
        self.addCleanup(restored.deleteLater)
        self.assertEqual(restored._missions["now"][0]["id"], second["id"])
        self.assertEqual(restored._continuity, board._continuity)

    def test_parking_a_thought_does_not_create_a_task(self):
        board = self._board()
        before = sum(len(items) for items in board._missions.values())
        board._capture_input.setText("Look up that unrelated article")
        board._capture_parking()

        self.assertEqual(sum(len(items) for items in board._missions.values()), before)
        self.assertEqual(board._parking_lot, ["Look up that unrelated article"])

        board._promote_parked_thought(0)
        self.assertEqual(board._parking_lot, [])
        self.assertEqual(board._missions["next"][0]["title"], "Look up that unrelated article")

    def test_complete_requires_confirmation_and_can_be_undone(self):
        board = self._board()
        mission = board.add_mission("Send the approved summary", "now")

        board._complete_selected()
        self.assertTrue(board._confirming_complete)
        self.assertEqual(board._missions["now"][0]["id"], mission["id"])
        self.assertIn("Preview", board._action_preview.text())

        board._complete_selected()
        self.assertEqual(board._missions["now"], [])
        self.assertEqual(board._missions["later"][0]["status"], "Completed")
        self.assertTrue(board._undo_action.isEnabled())

        board._undo_last_change()
        self.assertEqual(board._missions["now"][0]["id"], mission["id"])
        self.assertEqual(board._missions["later"], [])

    def test_reduced_choice_and_neutral_checkin_preferences_apply_live(self):
        board = self._board(max_choices=2, reduced_choices=True, checkin_minutes=5)
        self.assertFalse(board._continue_action.isHidden())
        self.assertFalse(board._breakdown_action.isHidden())
        self.assertTrue(board._complete_action.isHidden())
        self.assertTrue(board._checkin_timer.isActive())

        board._neutral_checkin()
        message = board._action_preview.text().lower()
        self.assertIn("continue", message)
        self.assertNotIn("overdue", message)
        self.assertNotIn("failed", message)

    def test_tool_activity_temporarily_takes_now_then_restores_user_context(self):
        board = self._board()
        mission = board.add_mission("Finish the interaction review", "now")

        board.ingest_task("Web Search", "calling")
        self.assertEqual(board._missions["now"][0]["title"], "Web Search")
        self.assertIn(mission["id"], [item["id"] for item in board._missions["next"]])

        board.ingest_task("Web Search", "done")
        self.assertEqual(board._missions["now"][0]["id"], mission["id"])
        self.assertEqual(board._selected["id"], mission["id"])
        self.assertIn("Resume", board._continuity)

    def test_mission_board_is_the_default_main_workspace(self):
        api_file = Path(self.temp_dir.name) / "api.json"
        with patch.object(ui, "API_FILE", api_file), \
             patch.object(ui, "get_secret_store", return_value=_NoSecrets()), \
             patch.object(ui.MainWindow, "_setup_system_tray", lambda self: None), \
             patch.object(ui.MainWindow, "_update_metrics", lambda self: None):
            window = ui.MainWindow("face.png")
            self.addCleanup(window.deleteLater)
            self.assertTrue(window._command_center_open)
            self.assertIs(window._workspace_stack.currentWidget(), window._mission_board)
            self.assertEqual(window._splitter.sizes()[0], 0)
            self.assertEqual(ui.ThemeManager.current_name(), "calm_mint")

            window._set_command_center(False, announce=False)
            self.assertIs(window._workspace_stack.currentWidget(), window.hud)
            window._set_command_center(True, announce=False)
            self.assertIs(window._workspace_stack.currentWidget(), window._mission_board)


if __name__ == "__main__":
    unittest.main()
