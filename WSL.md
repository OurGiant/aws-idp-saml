# Running on WSL

This utility runs under Windows Subsystem for Linux (WSL) the same way it runs on native Linux - [Browser.py](Browser.py) detects `sys.platform == 'linux'` either way and can't tell the difference. In practice, though, a fresh WSL distro (this was verified on Ubuntu 24.04) is missing a couple of things a desktop Linux install normally has, and Ubuntu's default Chromium package doesn't work with Selenium at all. This doc covers what to install and why.

## Quick setup

```bash
sudo apt update
sudo apt install -y firefox python3-pip python3-venv libasound2t64
wget -q -O /tmp/google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install -y /tmp/google-chrome.deb
```

Then install the project as usual (see the main [README](README.md#installation)). The rest of this doc explains why each piece is there.

## Firefox: use the apt package, it's really a snap

`sudo apt install firefox` on Ubuntu 22.04+ actually installs a transitional package that pulls in the Firefox **snap**. That's fine - [Browser.py](Browser.py)'s `gecko_from_snap()` already detects a snap install (by checking for `/snap/firefox/current/usr/lib/firefox`) and points Selenium at the binary inside it. No extra configuration needed; `--browser firefox` works out of the box once the package (and `libasound2t64`, below) is installed.

## Chrome: don't use the `chromium-browser` apt package

`sudo apt install chromium-browser` also resolves to a snap on Ubuntu 24.04, but unlike Firefox's snap, Chromium's is **strictly confined**, and that confinement is incompatible with external Selenium/chromedriver automation. Selenium Manager downloads a standalone chromedriver binary that runs *outside* the snap's sandbox, and it can't see the `DevToolsActivePort` file the confined Chrome process writes - every launch attempt fails with:

```
session not created: DevToolsActivePort file doesn't exist
```

This isn't a config issue or something more dependencies will fix - it's a fundamental mismatch between snap confinement and how chromedriver talks to the browser. The fix is to install real Google Chrome instead, which ships as a plain `.deb` outside of snap:

```bash
wget -q -O /tmp/google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install -y /tmp/google-chrome.deb
```

Reference it as `--browser chrome` as usual - [Browser.py](Browser.py) doesn't set an explicit binary location for Chrome, so Selenium Manager finds `google-chrome` on `PATH` automatically.

## Missing library: libasound2t64

Minimal WSL images don't ship ALSA (`libasound.so.2`) at all - `dpkg -l | grep asound` comes back empty. Both browsers need it to start under Selenium, even in headless mode:

- **Firefox** crashes immediately with `XPCOMGlueLoad error ... libasound.so.2: cannot open shared object file`.
- **Chromium/Chrome** don't crash outright, but this was a contributing factor to the slow `SessionNotCreatedException` timeout above.

Install it with:

```bash
sudo apt install -y libasound2t64
```

(Older Ubuntu releases may need `libasound2` instead - check with `apt-cache policy libasound2t64 libasound2`.)

## `--debug` (visible browser) mode needs WSLg

Headless mode (the default) doesn't need a display. If you pass `--debug` to see the browser window, it needs an X/Wayland display - WSLg provides this automatically on Windows 11 and recent Windows 10 builds. Check it's present with:

```bash
echo $DISPLAY $WAYLAND_DISPLAY
```

If both are empty, `--debug` will fail to open a window; headless mode is unaffected.

## Verified

Tested on Ubuntu 24.04 (WSL2) with the packages above installed, chrome and firefox each in both headless and `--debug` mode - all four combinations launch, load a page, and quit cleanly via [Browser.py](Browser.py)'s `setup_browser()`.

Not covered here: Edge (no supported Linux package to test against) and corporate proxy/firewall behavior around Selenium Manager's driver-download endpoint. See issue [#93](https://github.com/OurGiant/aws-idp-saml/issues/93) for the full cross-platform test matrix this is part of.
