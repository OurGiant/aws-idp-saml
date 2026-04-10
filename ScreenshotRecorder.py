# coding=utf-8
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from Logging import Logging

log_stream = Logging('screenshot_recorder')


class ScreenshotRecorder:
    """
    Manages screenshot recording for Selenium sessions.
    Can be enabled/disabled via command line flag: --enable-screenshots
    """

    _enabled: bool = False
    _screenshot_dir: Optional[str] = None
    _counter: int = 0

    @classmethod
    def initialize(cls, enable: bool = False, output_dir: Optional[str] = None) -> None:
        """
        Initialize the screenshot recorder.

        Args:
            enable (bool): Whether to enable screenshot recording
            output_dir (str, optional): Directory to save screenshots. 
                                       Defaults to ./screenshots/{timestamp}
        """
        cls._enabled = enable
        cls._counter = 0

        if enable:
            if output_dir is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_dir = f"screenshots/{timestamp}"

            cls._screenshot_dir = output_dir
            Path(cls._screenshot_dir).mkdir(parents=True, exist_ok=True)
            log_stream.info(f"Screenshot recording enabled. Output: {cls._screenshot_dir}")
        else:
            log_stream.info("Screenshot recording disabled")

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if screenshot recording is enabled."""
        return cls._enabled

    @classmethod
    def capture(cls, driver, label: str = "") -> Optional[str]:
        """
        Capture a screenshot if recording is enabled.

        Args:
            driver: Selenium WebDriver instance
            label (str, optional): Label for the screenshot (e.g., "login_page", "mfa_prompt")

        Returns:
            str: Path to saved screenshot, or None if recording is disabled
        """
        if not cls._enabled or cls._screenshot_dir is None:
            return None

        try:
            cls._counter += 1
            filename = f"{cls._counter:03d}"

            if label:
                filename += f"_{label}"

            filename += ".png"
            filepath = os.path.join(cls._screenshot_dir, filename)

            driver.save_screenshot(filepath)
            log_stream.debug(f"Screenshot saved: {filepath}")
            return filepath

        except Exception as e:
            log_stream.error(f"Failed to capture screenshot: {str(e)}")
            return None

    @classmethod
    def get_output_dir(cls) -> Optional[str]:
        """Get the current screenshot output directory."""
        return cls._screenshot_dir
