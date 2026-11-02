#!/usr/bin/python3
"""Observe standalone Super releases without grabbing or forwarding input."""
import selectors
import subprocess
import time

from evdev import InputDevice, ecodes as E, list_devices


class SuperTap:
    def __init__(self):
        self.held = set()
        self.candidate = None

    def reset(self):
        self.held.clear()
        self.candidate = None

    def feed(self, source, event):
        key = (source, event.code)
        if event.type == E.EV_SYN and event.code == E.SYN_DROPPED:
            self.reset()
        elif event.type == E.EV_KEY:
            if event.value == 1:
                self.candidate = key if event.code in (E.KEY_LEFTMETA, E.KEY_RIGHTMETA) and not self.held else None
                self.held.add(key)
            elif event.value == 0:
                fire = self.candidate == key
                self.held.discard(key)
                self.candidate = None
                return fire
        elif event.type == E.EV_REL and event.code in (
            E.REL_WHEEL, E.REL_HWHEEL, E.REL_WHEEL_HI_RES, E.REL_HWHEEL_HI_RES
        ) and event.value:
            self.candidate = None
        elif event.type == E.EV_ABS:
            # Touchpad gestures must not open the overview on Super release.
            self.candidate = None
        return False


def main():
    selector = selectors.DefaultSelector()
    devices = {}
    state = SuperTap()
    scan_at = 0
    while True:
        if time.monotonic() >= scan_at:
            paths = set(list_devices())
            for path in set(devices) - paths:
                dev = devices.pop(path)
                selector.unregister(dev)
                dev.close()
                state.reset()
            for path in paths - set(devices):
                try:
                    dev = InputDevice(path)
                    caps = dev.capabilities()
                    if not any(kind in caps for kind in (E.EV_KEY, E.EV_REL, E.EV_ABS)):
                        dev.close()
                        continue
                    selector.register(dev, selectors.EVENT_READ, dev)
                    devices[path] = dev
                    state.candidate = None
                    state.held.update((path, key) for key in dev.active_keys())
                except OSError:
                    continue
            scan_at = time.monotonic() + 2
        events = []
        for selected, _ in selector.select(timeout=0.1):
            dev = selected.data
            try:
                events.extend((event.timestamp(), dev.path, event) for event in dev.read())
            except BlockingIOError:
                pass
            except OSError:
                selector.unregister(dev)
                devices.pop(dev.path, None)
                dev.close()
                state.reset()
        events.sort(key=lambda item: item[0])
        for _, path, event in events:
            if state.feed(path, event):
                try:
                    subprocess.run(['niri', 'msg', 'action', 'toggle-overview'],
                                   timeout=2, check=False)
                except subprocess.TimeoutExpired:
                    pass


if __name__ == '__main__':
    main()
