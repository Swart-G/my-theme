"""Verify standalone Win detection without input hardware or evdev installed."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch


E = SimpleNamespace(EV_SYN=0, EV_KEY=1, EV_REL=2, EV_ABS=3,
                    SYN_DROPPED=3, KEY_LEFTMETA=125, KEY_RIGHTMETA=126,
                    REL_WHEEL=8, REL_HWHEEL=6, REL_WHEEL_HI_RES=11,
                    REL_HWHEEL_HI_RES=12)
spec = importlib.util.spec_from_file_location(
    'super_tap', Path(__file__).resolve().parents[1] / 'noctalia/niri/super-tap.py')
module = importlib.util.module_from_spec(spec)
with patch.dict('sys.modules', {'evdev': SimpleNamespace(
        InputDevice=None, ecodes=E, list_devices=None)}):
    spec.loader.exec_module(module)


class SuperTapTests(unittest.TestCase):
    def setUp(self):
        self.state = module.SuperTap()

    def feed(self, code, value, kind=E.EV_KEY, source='keyboard'):
        return self.state.feed(source, SimpleNamespace(type=kind, code=code, value=value))

    def test_either_win_key_triggers_only_on_release(self):
        for code in (E.KEY_LEFTMETA, E.KEY_RIGHTMETA):
            self.assertFalse(self.feed(code, 1))
            self.assertTrue(self.feed(code, 0))
            self.assertFalse(self.feed(code, 0))

    def test_shortcut_on_another_device_cancels_overview(self):
        self.feed(E.KEY_LEFTMETA, 1)
        self.feed(18, 1, source='second-keyboard')
        self.feed(18, 0, source='second-keyboard')
        self.assertFalse(self.feed(E.KEY_LEFTMETA, 0))

    def test_preexisting_modifier_cancels_overview(self):
        self.feed(29, 1)
        self.feed(E.KEY_LEFTMETA, 1)
        self.assertFalse(self.feed(E.KEY_LEFTMETA, 0))

    def test_scroll_in_either_axis_cancels_overview(self):
        for axis in (E.REL_WHEEL, E.REL_HWHEEL, E.REL_WHEEL_HI_RES, E.REL_HWHEEL_HI_RES):
            with self.subTest(axis=axis):
                self.feed(E.KEY_LEFTMETA, 1)
                self.feed(axis, 1, E.EV_REL, 'mouse')
                self.assertFalse(self.feed(E.KEY_LEFTMETA, 0))

    def test_click_or_touchpad_motion_cancels_overview(self):
        for kind, code in ((E.EV_KEY, 272), (E.EV_ABS, 0)):
            with self.subTest(kind=kind):
                self.state.reset()
                self.feed(E.KEY_LEFTMETA, 1)
                self.feed(code, 1, kind, 'pointer')
                self.assertFalse(self.feed(E.KEY_LEFTMETA, 0))

    def test_lost_events_cancel_candidate_and_recover(self):
        self.feed(E.KEY_LEFTMETA, 1)
        self.feed(E.SYN_DROPPED, 0, E.EV_SYN)
        self.assertFalse(self.feed(E.KEY_LEFTMETA, 0))
        self.feed(E.KEY_LEFTMETA, 1)
        self.assertTrue(self.feed(E.KEY_LEFTMETA, 0))
