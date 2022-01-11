import time
import threading
import logging

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver import FirefoxProfile

logger = logging.getLogger('framework.parallelization')


class WebdriverManager:
    def __init__(self, limiter, enable_tracker_blocking=True, enable_caching=True):
        self.lock = threading.RLock()
        self.limiter = limiter
        self.enable_tracker_blocking = enable_tracker_blocking
        self.enable_caching = enable_caching
        self.active_instances = list()
        self.free_instances = list()

    def request(self) -> webdriver.Firefox:  # TODO: make a context manager out of `request()` and `release()` methods
        with self.lock:
            if len(self.free_instances) > 0:
                return self.free_instances.pop()

            logger.info(f"No free webdriver available, starting webdriver №{len(self.active_instances) + 1}")
            driver = self._try_to_run()

            while driver is None:
                logger.debug("Webdriver failed to start, retrying in 10 seconds...")
                time.sleep(10)
                driver = self._try_to_run()
            logger.debug("Webdriver started, setting limiter and returning")
            driver.limiter = self.limiter
            self.active_instances.append(driver)
        return driver

    def release(self, webdriver_instance: webdriver.Firefox) -> None:
        with self.lock:
            if webdriver_instance not in self.active_instances:
                logger.warning("Release of non-managed webdriver instance requested, ignoring")
                return
            self.free_instances.append(webdriver_instance)

    def close_all(self) -> None:
        with self.lock:
            for driver in self.active_instances:
                driver.quit()

    def _try_to_run(self) -> webdriver.Firefox:
        driver = None
        logger.debug("====>Launching firefox")

        try:
            profile = FirefoxProfile()
            if self.enable_caching:
                profile.set_preference("network.proxy.type", 1)
                profile.set_preference("network.proxy.http", "cache")
                profile.set_preference("network.proxy.http_port", 3128)
                profile.set_preference("network.proxy.ssl", "cache")
                profile.set_preference("network.proxy.ssl_port", 3128)
                profile.set_preference("network.proxy.ftp", "cache")
                profile.set_preference("network.proxy.ftp_port", 3128)
                profile.set_preference("network.proxy.backup.ssl", "")
                profile.set_preference("network.proxy.backup.ssl_port", 0)
                profile.set_preference("network.proxy.backup.ftp", "")
                profile.set_preference("network.proxy.backup.ftp_port", 0)
                profile.set_preference("network.proxy.share_proxy_settings", True)
                profile.set_preference("dom.disable_beforeunload", True)
                profile.set_preference('useAutomationExtension', False)
            if self.enable_tracker_blocking:
                profile.set_preference("browser.contentblocking.category", "strict")
            driver = webdriver.Firefox(profile)
            driver.set_page_load_timeout(180)
            driver.set_window_size(1920, 1080)
            logger.debug("====>Firefox launched")
        except WebDriverException:
            logger.error("Failed to start firefox")
            logger.error(str(WebDriverException))
        return driver
