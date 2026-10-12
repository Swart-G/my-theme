#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Meta + wheel desktop switching, matching the original local service."""
import subprocess
import shutil
import time
from pathlib import Path
import selectors
from evdev import InputDevice, UInput, list_devices, ecodes

META_KEYS = {ecodes.KEY_LEFTMETA, ecodes.KEY_RIGHTMETA}
WHEEL_CODES = {
    code for code in (
        getattr(ecodes, "REL_WHEEL", None),
        getattr(ecodes, "REL_WHEEL_HI_RES", None),
    ) if code is not None
}
meta_down = set()
wheel_devices = []
grabbed_wheel_devices = set()
forwarded_mouse = None

def find_qdbus():
    for path in ('/usr/lib64/qt6/bin/qdbus', '/usr/lib/qt6/bin/qdbus'):
        if Path(path).is_file():
            return path
    executable = shutil.which('qdbus6') or shutil.which('qdbus')
    if not executable:
        raise RuntimeError('Qt6 qdbus is required')
    return executable


def switch(direction):
    action = "Switch to Next Desktop" if direction > 0 else "Switch to Previous Desktop"
    subprocess.run(
        [find_qdbus(), "org.kde.kglobalaccel", "/component/kwin",
         "org.kde.kglobalaccel.Component.invokeShortcut", action],
        check=False
    )

def set_wheel_grabbed(grabbed):
    for dev in wheel_devices:
        if grabbed and dev.fd not in grabbed_wheel_devices:
            try:
                dev.grab()
                grabbed_wheel_devices.add(dev.fd)
            except OSError as exc:
                print(f"Could not grab {dev.path} ({dev.name}): {exc}", flush=True)
        elif not grabbed and dev.fd in grabbed_wheel_devices:
            try:
                dev.ungrab()
            except OSError as exc:
                print(f"Could not ungrab {dev.path} ({dev.name}): {exc}", flush=True)
            finally:
                grabbed_wheel_devices.discard(dev.fd)

def should_suppress(event):
    return event.type == ecodes.EV_REL and event.code in WHEEL_CODES

def forward_if_grabbed(dev, event):
    if dev.fd not in grabbed_wheel_devices:
        return False

    if not should_suppress(event) and forwarded_mouse is not None:
        forwarded_mouse.write_event(event)

    return True

def main():
    global forwarded_mouse
    # Собираем устройства: те, что умеют клавиши, и те, что умеют колесо
    devices = []
    for path in list_devices():
        dev = InputDevice(path)
        if dev.name == "meta-wheel-forwarded-mouse":
            dev.close()
        else:
            devices.append(dev)
    find_qdbus()
    sel = selectors.DefaultSelector()

    for dev in devices:
        caps = dev.capabilities()
        has_keys = ecodes.EV_KEY in caps
        has_wheel = ecodes.EV_REL in caps and ecodes.REL_WHEEL in caps.get(ecodes.EV_REL, [])
        if has_keys or has_wheel:
            sel.register(dev, selectors.EVENT_READ, dev)
        if has_wheel:
            wheel_devices.append(dev)

    if not wheel_devices or not any(META_KEYS.intersection(dev.capabilities().get(ecodes.EV_KEY, [])) for dev in devices):
        raise RuntimeError("Keyboard/mouse access is missing; check Rodip Glass input permissions")

    if wheel_devices:
        forwarded_mouse = UInput.from_device(*wheel_devices, name="meta-wheel-forwarded-mouse")

    print("Listening... (Meta + scroll переключает рабочие столы)")

    device_paths = {dev.path for dev in devices}
    last_scan = time.monotonic()
    while True:
        # Restart through systemd on hotplug to recreate the virtual mouse with
        # the new device capabilities. Never read our own forwarded events.
        if time.monotonic() - last_scan >= 2:
            paths = set(list_devices())
            if forwarded_mouse is not None and forwarded_mouse.device is not None:
                paths.discard(forwarded_mouse.device.path)
            if paths != device_paths:
                raise RuntimeError("Input devices changed; restarting listener")
            last_scan = time.monotonic()
        for key, _ in sel.select(timeout=2):
            dev = key.data
            for event in dev.read():
                forwarded = forward_if_grabbed(dev, event)

                if event.type == ecodes.EV_KEY and event.code in META_KEYS:
                    was_held = bool(meta_down)
                    if event.value == 1:      # нажата
                        meta_down.add(event.code)
                    elif event.value == 0:    # отпущена
                        meta_down.discard(event.code)

                    is_held = bool(meta_down)
                    if is_held != was_held:
                        set_wheel_grabbed(is_held)
                elif event.type == ecodes.EV_REL and event.code == ecodes.REL_WHEEL:
                    if meta_down and event.value != 0:
                        switch(-event.value)  # направление инвертировано; событие забрано grab()
                    elif forwarded:
                        continue


if __name__ == '__main__':
    main()
