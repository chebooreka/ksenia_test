from playwright.async_api import Page
import logging

logger = logging.getLogger(__name__)


class BasePage:
    def __init__(self, page: Page):
        self.page = page
        self.timeout = 10000

    async def navigate(self, url: str):
        await self.page.goto(url)
        await self.page.wait_for_timeout(2000)

    async def wait_for_selector(self, selector: str, timeout: int = None):
        timeout = timeout or self.timeout
        await self.page.wait_for_selector(selector, timeout=timeout)

    async def take_screenshot(self, name: str):
        await self.page.screenshot(path=f"screenshots/{name}.png")