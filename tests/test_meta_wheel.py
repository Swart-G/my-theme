# SPDX-License-Identifier: MIT
import importlib.util, json, sys, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1]
def load(name):
 spec=importlib.util.spec_from_file_location(name.replace('-','_'),ROOT/'scripts'/(name+'.py'))
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 return module

class MetaWheelTests(unittest.TestCase):
 def test_meta_wheel_up_goes_previous_and_down_goes_next(self):
  try:wheel=load('meta-wheel-desktops')
  except ImportError:self.skipTest('Python evdev is not installed')
  keyboard=Mock(path='/dev/input/keyboard',fd=10);keyboard.name='keyboard'
  keyboard.capabilities.return_value={wheel.ecodes.EV_KEY:[wheel.ecodes.KEY_LEFTMETA]}
  keyboard.read.return_value=[SimpleNamespace(type=wheel.ecodes.EV_KEY,code=wheel.ecodes.KEY_LEFTMETA,value=1)]
  mouse=Mock(path='/dev/input/mouse',fd=11);mouse.name='mouse'
  mouse.capabilities.return_value={wheel.ecodes.EV_REL:[wheel.ecodes.REL_WHEEL]}
  mouse.read.return_value=[SimpleNamespace(type=wheel.ecodes.EV_REL,code=wheel.ecodes.REL_WHEEL,value=value) for value in [1,-1]]
  selector=Mock();selector.select.side_effect=[[(SimpleNamespace(data=keyboard),None),(SimpleNamespace(data=mouse),None)],RuntimeError('test finished')]
  with patch.object(wheel,'list_devices',return_value=[keyboard.path,mouse.path]),patch.object(wheel,'InputDevice',side_effect=[keyboard,mouse]),patch.object(wheel,'find_qdbus',return_value='/qt6/qdbus'),patch.object(wheel.selectors,'DefaultSelector',return_value=selector),patch.object(wheel.UInput,'from_device'),patch.object(wheel.time,'monotonic',return_value=0),patch.object(wheel.subprocess,'run') as run:
   with self.assertRaisesRegex(RuntimeError,'test finished'):wheel.main()
   self.assertEqual([call.args[0][-1] for call in run.call_args_list],['Switch to Previous Desktop','Switch to Next Desktop'])

 def test_switch_and_forwarding_preserve_mouse_events(self):
  try:wheel=load('meta-wheel-desktops')
  except ImportError:self.skipTest('Python evdev is not installed')
  with patch.object(wheel,'find_qdbus',return_value='/qt6/qdbus'),patch.object(wheel.subprocess,'run') as run:
   wheel.switch(-1);self.assertEqual(run.call_args.args[0][-1],'Switch to Previous Desktop')
   wheel.switch(1);self.assertEqual(run.call_args.args[0][-1],'Switch to Next Desktop')
  device=SimpleNamespace(fd=10);wheel.grabbed_wheel_devices.add(10);wheel.forwarded_mouse=Mock()
  for code in wheel.WHEEL_CODES:
   self.assertTrue(wheel.forward_if_grabbed(device,SimpleNamespace(type=wheel.ecodes.EV_REL,code=code)))
  wheel.forwarded_mouse.write_event.assert_not_called()
  for event in [SimpleNamespace(type=wheel.ecodes.EV_REL,code=wheel.ecodes.REL_X),SimpleNamespace(type=wheel.ecodes.EV_KEY,code=wheel.ecodes.BTN_LEFT),SimpleNamespace(type=wheel.ecodes.EV_SYN,code=wheel.ecodes.SYN_REPORT)]:
   self.assertTrue(wheel.forward_if_grabbed(device,event))
  self.assertEqual(wheel.forwarded_mouse.write_event.call_count,3)
  wheel.grabbed_wheel_devices.clear()
  self.assertFalse(wheel.forward_if_grabbed(device,SimpleNamespace(type=wheel.ecodes.EV_REL,code=wheel.ecodes.REL_X)))

 def test_input_setup_restores_original_rules_and_module_settings(self):
  helper=load('input-install')
  with tempfile.TemporaryDirectory() as temp:
   base=Path(temp);rule=base/'input.rules';rule.write_text('original rules\n');module=base/'uinput.conf'
   with patch.object(helper,'RULE',rule),patch.object(helper,'MODULE',module),patch.object(helper,'BACKUPS',base/'backups'),patch.object(helper,'refresh'),patch.object(helper.subprocess,'run'),patch.object(helper.shutil,'which',return_value=None):
    receipt=helper.install()
    self.assertIn('TAG+="uaccess"',rule.read_text());self.assertEqual(module.read_text(),'uinput\n')
    helper.restore(Path(receipt['backup']))
    self.assertEqual(rule.read_text(),'original rules\n');self.assertFalse(module.exists())

 def test_input_setup_rolls_back_on_module_failure(self):
  helper=load('input-install')
  with tempfile.TemporaryDirectory() as temp:
   base=Path(temp);rule=base/'input.rules';rule.write_text('original rules\n');module=base/'uinput.conf'
   with patch.object(helper,'RULE',rule),patch.object(helper,'MODULE',module),patch.object(helper,'BACKUPS',base/'backups'),patch.object(helper,'refresh'),patch.object(helper.subprocess,'run',side_effect=RuntimeError('modprobe failed')):
    with self.assertRaisesRegex(RuntimeError,'modprobe failed'):helper.install()
    self.assertEqual(rule.read_text(),'original rules\n');self.assertFalse(module.exists())
