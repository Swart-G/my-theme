# Third-party components

- Glass Panel by zhelly0: https://github.com/zhelly0/glass-panel-theme — GPL-3.0. Source and license in `theme/`. Local panel-background SVG adjustments retain that license.
- KDE Control Station by EliverLara: https://github.com/EliverLara/kde-control-station (plasma6) — GPL-3.0. Source, translations, license and upstream documentation in `plasmoids/KdeControlStation/`. Local edits fix Plasma 6 preferred representation and compact icon alignment.
- Bart Aurorae decoration by jomada: https://store.kde.org/p/2324915 — GPL-3.0. Unmodified source and license in `terminal/decoration-source/`; generated copies follow the KDE wallpaper accent. The installed original Bart is preserved.
- Custom panel, dashboard, desktop switcher, KWin script, installer and login theme use MIT notices in their source files. The distributed collection is licensed GPL-3.0.

The global-theme preview uses the upstream Glass Panel screenshot already distributed in `theme/docs/`. The lock-screen package is generated from the installed KDE source files, preserving their SPDX notices and native authentication code.

The installers use modules provided by the operating system; they do not redistribute those modules. Personal account details, credentials and prebuilt native binaries are not included.

## Niri / Noctalia profile

- `noctalia/gtk/Lavanda-Sea/` contains the installed GTK 2/3/4 Lavanda-Sea
  stylesheets and image assets by vinceliuice (GPL-3.0), with the upstream
  license. Source: https://github.com/vinceliuice/Lavanda-gtk-theme. The
  snapshot preserves the current local theme; generated CSS/assets are unmodified.

- Niri, Noctalia and Noctalia Greeter are installed as distribution packages:
  https://github.com/niri-wm/niri, https://github.com/noctalia-dev/noctalia,
  https://github.com/noctalia-dev/noctalia-greeter. Their source is not vendored.
- The Niri/Alacritty configuration was adapted locally with reference to the
  Niri showcase and https://github.com/YaLTeR/dotfiles. The terminal uses
  Catppuccin Mocha color values (https://github.com/catppuccin/alacritty, MIT).
- The wallpaper is downloaded at install time from
  https://github.com/orangci/walls/blob/master/train-station.jpg. It is not
  included or relicensed here; `--wallpaper` accepts an image of your choice.
  SHA256 is pinned in the installer.
- `noctalia/system/RPM-GPG-KEY-terra44` is the public Terra 44 signing key from
  the official `terra-gpg-keys-44-6.noarch.rpm` at https://repos.fyralabs.com/terra44/.
  Fingerprint: `AE09157A4DE88B497EA1D5D300CDAB43DE226D6F`.
