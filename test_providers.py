# coding=utf-8
"""Unit tests for the forced Okta password-reset screen detection (#95)."""

from unittest.mock import MagicMock, patch

import Providers
from SeleniumHelper import SeleniumHelper


def test_forced_password_reset_screen_detected():
    driver = MagicMock()
    wait = MagicMock()

    with patch.object(SeleniumHelper, "poll_page_source_with_backoff", return_value=True) as poll, \
         patch.object(Providers.ScreenshotRecorder, "capture") as capture:
        detected = Providers.check_for_forced_password_reset_screen(driver, wait)

    assert detected is True
    assert poll.call_args.args[0] == Providers.forced_password_reset_indicator
    capture.assert_called_once_with(driver, "forced_password_reset_screen")


def test_forced_password_reset_screen_not_detected():
    driver = MagicMock()
    wait = MagicMock()

    with patch.object(SeleniumHelper, "poll_page_source_with_backoff", return_value=False), \
         patch.object(Providers.ScreenshotRecorder, "capture") as capture:
        detected = Providers.check_for_forced_password_reset_screen(driver, wait)

    assert detected is False
    capture.assert_not_called()


def test_forced_password_reset_screen_swallows_errors():
    driver = MagicMock()
    wait = MagicMock()

    with patch.object(SeleniumHelper, "poll_page_source_with_backoff", side_effect=RuntimeError("boom")):
        detected = Providers.check_for_forced_password_reset_screen(driver, wait)

    assert detected is False


def test_indicator_matches_realistic_password_reset_markup():
    driver = MagicMock()
    driver.page_source = (
        "<html><body><h1>Reset your Okta password</h1>"
        "<input name=\"newPassword\"/><input name=\"confirmPassword\"/>"
        "<button>Reset Password</button></body></html>"
    )
    helper = SeleniumHelper(driver, wait=MagicMock())

    assert helper.poll_page_source_with_backoff(
        Providers.forced_password_reset_indicator, max_total_seconds=1, label="test"
    ) is True


def test_indicator_does_not_match_mfa_selection_markup():
    driver = MagicMock()
    driver.page_source = (
        '<html><body><a class="button select-factor link-button">Select Okta Verify.</a></body></html>'
    )
    helper = SeleniumHelper(driver, wait=MagicMock())

    assert helper.poll_page_source_with_backoff(
        Providers.forced_password_reset_indicator, max_total_seconds=0.05, label="test"
    ) is False
