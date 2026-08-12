# coding=utf-8
"""
Selenium helper utilities to reduce code duplication and improve maintainability.
Provides common patterns for element interaction and waiting.
"""

import time

from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common import exceptions as se
from Logging import Logging

log_stream = Logging('selenium_helper')


class SeleniumHelper:
    """Helper class for common Selenium operations."""

    def __init__(self, driver, wait: WebDriverWait):
        """
        Initialize the helper with a driver and wait instance.

        Args:
            driver: Selenium WebDriver instance
            wait (WebDriverWait): WebDriverWait instance for explicit waits
        """
        self.driver = driver
        self.wait = wait

    def click_element(self, locator, label: str = ""):
        """
        Wait for element to be clickable and click it.

        Args:
            locator (tuple): Tuple of (By.*, selector_string)
            label (str, optional): Description for logging

        Returns:
            bool: True if successful, False otherwise

        Raises:
            TimeoutException: If element not found within timeout
            ElementClickInterceptedException: If click is intercepted
        """
        try:
            element = self.wait.until(ec.element_to_be_clickable(locator))
            log_stream.debug(f'Element clickable {label}')
            element.click()
            log_stream.debug(f'Clicked element {label}')
            return True
        except se.TimeoutException:
            log_stream.warning(f'Timeout waiting for clickable element {label}')
            raise
        except se.ElementClickInterceptedException as e:
            log_stream.warning(f'Click intercepted for element {label}: {str(e)}')
            raise

    def enter_text(self, locator, text: str, label: str = ""):
        """
        Wait for element to be clickable, clear it, and send text.

        Args:
            locator (tuple): Tuple of (By.*, selector_string)
            text (str): Text to enter
            label (str, optional): Description for logging

        Returns:
            bool: True if successful, False otherwise

        Raises:
            TimeoutException: If element not found within timeout
        """
        try:
            element = self.wait.until(ec.element_to_be_clickable(locator))
            element.clear()
            element.send_keys(text)
            log_stream.debug(f'Entered text into element {label}')
            return True
        except se.TimeoutException:
            log_stream.warning(f'Timeout waiting for element {label}')
            raise
        except se.NoSuchElementException as e:
            log_stream.warning(f'Element not found {label}: {str(e)}')
            raise

    def find_element(self, locator, label: str = ""):
        """
        Find an element without waiting.

        Args:
            locator (tuple): Tuple of (By.*, selector_string)
            label (str, optional): Description for logging

        Returns:
            WebElement: The found element

        Raises:
            NoSuchElementException: If element not found
        """
        try:
            element = self.driver.find_element(*locator)
            log_stream.debug(f'Found element {label}')
            return element
        except se.NoSuchElementException as e:
            log_stream.warning(f'Element not found {label}: {str(e)}')
            raise

    def wait_for_element(self, locator, label: str = ""):
        """
        Wait for element to be present (not necessarily clickable).

        Args:
            locator (tuple): Tuple of (By.*, selector_string)
            label (str, optional): Description for logging

        Returns:
            WebElement: The found element

        Raises:
            TimeoutException: If element not found within timeout
        """
        try:
            element = self.wait.until(ec.presence_of_element_located(locator))
            log_stream.debug(f'Element present {label}')
            return element
        except se.TimeoutException:
            log_stream.warning(f'Timeout waiting for element {label}')
            raise

    def poll_page_source_with_backoff(self, needle: str, max_total_seconds: float, label: str = "",
                                       initial_delay: float = 1, max_delay: float = 4, backoff_factor: float = 2):
        """
        Poll the page source for a substring, backing off exponentially between
        attempts instead of checking once after a single fixed-duration wait.
        Slow-rendering pages (e.g. Okta's factor-selection screen on Firefox)
        get repeated chances to finish rendering, while fast pages return on
        the first attempt. Bounded by an overall deadline so it always finishes.

        Args:
            needle (str): Substring to search for in the page source
            max_total_seconds (float): Overall deadline for polling, in seconds
            label (str, optional): Description for logging
            initial_delay (float): Seconds to wait before the first retry
            max_delay (float): Cap on the delay between retries
            backoff_factor (float): Multiplier applied to the delay after each miss

        Returns:
            bool: True if the substring was found before the deadline, False otherwise
        """
        deadline = time.monotonic() + max_total_seconds
        delay = initial_delay
        attempt = 0
        while True:
            attempt += 1
            if needle in self.driver.page_source:
                log_stream.debug(f'Found {label} in page source on attempt {attempt}')
                return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                log_stream.warning(f'Timeout waiting for {label} in page source after {attempt} attempts')
                return False
            time.sleep(min(delay, remaining))
            delay = min(delay * backoff_factor, max_delay)

    def wait_for_url_contains(self, url_fragment: str):
        """
        Wait for URL to contain a specific fragment.

        Args:
            url_fragment (str): Fragment that should appear in URL

        Returns:
            bool: True when URL contains fragment

        Raises:
            TimeoutException: If URL doesn't contain fragment within timeout
        """
        try:
            self.wait.until(lambda driver: url_fragment in driver.current_url)
            log_stream.debug(f'URL contains {url_fragment}')
            return True
        except se.TimeoutException:
            log_stream.warning(f'Timeout waiting for URL to contain {url_fragment}')
            raise
