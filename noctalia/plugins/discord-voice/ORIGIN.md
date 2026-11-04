# Discord Voice

Source: https://github.com/noctalia-dev/community-plugins/tree/e826a790860133f00461bf53257ea6f50ebdf623/discord-voice
Author: raycursive. Version: 0.3.3. License: MIT (declared in plugin.toml).

The local bar.luau fix uses native setGlyph/setGlyphColor/setText nodes rather
than barWidget.render. It keeps the Discord glyph stable during speaker,
channel and connection changes on the vertical Noctalia 5.4 bar. Status text
while disconnected is moved into the tooltip so it cannot widen the bar.
The panel and bridge are included so a clean install has the whole plugin.
The configured executable uses the native/Flatpak launcher bundled here.
No account tokens, channel history or avatar caches are included.
