# Running on WSL

This utility runs under Windows Subsystem for Linux (WSL) the same way it runs on native Linux - [Browser.py](Browser.py) detects `sys.platform == 'linux'` either way and can't tell the difference. In practice, though, a fresh WSL distro (this was verified on Ubuntu 24.04) is missing a couple of things a desktop Linux install normally has, and Ubuntu's default Chromium package doesn't work with Selenium at all. This doc covers what to install and why.

## Quick setup

```bash
sudo apt update
sudo apt install -y firefox libasound2t64
```

Chrome is optional — Selenium Manager will download Chrome for Testing automatically if `google-chrome` isn't on PATH. If you'd rather use the system browser (faster startup, no download):

```bash
wget -q -O /tmp/google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install -y /tmp/google-chrome.deb
```

Then install `uv` (if not already present) and run:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv run samlstat --help
```

The rest of this doc explains why each piece is there.

## Firefox: apt package, native or snap

`sudo apt install firefox` is the right command regardless of Ubuntu version, but what it installs has changed over time:

- **Ubuntu 22.04**: installs a transitional snap — Firefox lives at `/snap/firefox/current/usr/lib/firefox`. [Browser.py](Browser.py)'s `gecko_from_snap()` detects this and points Selenium at the binary inside the snap automatically.
- **Ubuntu 24.04** (verified): installs a plain native binary at `/usr/bin/firefox` — the snap dir is absent, `gecko_from_snap()` returns `(None, None)`, and Selenium Manager finds `firefox` on PATH directly.

Both paths work; no extra configuration is needed either way.

## Chrome: don't use the `chromium-browser` apt package

`sudo apt install chromium-browser` resolves to a **strictly confined** snap on Ubuntu 24.04. That confinement is incompatible with external Selenium/chromedriver automation — chromedriver runs outside the snap sandbox and can't see the `DevToolsActivePort` file the browser writes, so every launch fails with:

```
session not created: DevToolsActivePort file doesn't exist
```

There are two working alternatives:

**Option A — let Selenium Manager provision it (no install needed)**
Selenium Manager will detect that no system Chrome is present and download a standalone Chrome for Testing binary automatically. `--browser chrome` works out of the box.

**Option B — install real Google Chrome**
Gives faster startup and avoids the download on first run:

```bash
wget -q -O /tmp/google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install -y /tmp/google-chrome.deb
```

[Browser.py](Browser.py) doesn't set an explicit binary location for Chrome, so Selenium Manager finds `google-chrome` on PATH automatically when it's present.

## Missing library: libasound2t64

Minimal WSL images don't ship ALSA (`libasound.so.2`) at all. Both browsers need it to start under Selenium, even in headless mode:

- **Firefox** crashes immediately with `XPCOMGlueLoad error ... libasound.so.2: cannot open shared object file`.
- **Chrome** doesn't crash outright but this was a contributing factor to slow `SessionNotCreatedException` timeouts.

Install it with:

```bash
sudo apt install -y libasound2t64
```

(Older Ubuntu releases may need `libasound2` instead — check with `apt-cache policy libasound2t64 libasound2`.)

## `--debug` (visible browser) mode needs WSLg

Headless mode (the default) doesn't need a display. If you pass `--debug` to see the browser window, it needs an X/Wayland display — WSLg provides this automatically on Windows 11 and recent Windows 10 builds. Check it's present with:

```bash
echo $DISPLAY $WAYLAND_DISPLAY
```

If both are empty, `--debug` will fail to open a window; headless mode is unaffected.

## Verified

Tested on Ubuntu 24.04 (WSL2) with the packages above installed, Chrome and Firefox each in both headless and `--debug` mode — all four combinations launch, load a page, and quit cleanly via [Browser.py](Browser.py)'s `setup_browser()`. Chrome ran via Selenium Manager's auto-provisioned Chrome for Testing (no system Chrome installed); Firefox ran as a native apt binary (no snap).

Not covered here: Edge (no supported Linux package) and corporate proxy/firewall behavior around Selenium Manager's driver-download endpoint. See issue [#93](https://github.com/OurGiant/aws-idp-saml/issues/93) for the full cross-platform test matrix.
