from .base_page import BasePage
from typing import List, Dict, Optional
import logging
import re
import random

logger = logging.getLogger(__name__)


class OzonSearchPage(BasePage):
    PRODUCT_LINKS = 'a[href*="/product/"]'
    LOAD_MORE_SPINNER = '.loading-spinner'

    def __init__(self, page):
        super().__init__(page)
        self.found_positions: List[Dict] = []

    async def search_by_query_params(self, query_params):
        search_url = query_params.to_query_string()
        await self.navigate(search_url)
        await self.page.wait_for_timeout(3000)

    async def scroll_to_load_more_products(self, target_count: int,
                                           max_scrolls: int = 30):
        all_urls = set()
        scroll_attempts = 0

        while len(all_urls) < target_count and scroll_attempts < max_scrolls:
            current_urls = await self._get_current_product_urls()
            all_urls.update(current_urls)

            logger.debug(
                f"просмотр {scroll_attempts + 1}, уникальных URL: {len(all_urls)}")

            if len(all_urls) >= target_count:
                break

            await self._scroll_down()
            await self._wait_for_loading()

            scroll_attempts += 1

        return list(all_urls)[:target_count]

    async def _get_current_product_urls(self):
        return await self.page.evaluate('''() => {
            return Array.from(document.querySelectorAll('a[href*="/product/"]'))
                .map(link => link.href)
                .filter(href => href);
        }''')

    async def _scroll_down(self):
        await self.page.evaluate('window.scrollBy(0, 800)')
        await self.page.wait_for_timeout(random.randint(1500, 2500))

    async def _wait_for_loading(self):
        try:
            await self.page.wait_for_selector(self.PRODUCT_LINKS, timeout=2000)
        except:
            pass

    async def extract_product_positions(self, urls: List[str],
                                        find_skus: Optional[List[int]] = None):
        if find_skus is None:
            find_skus = []

        found_positions = []
        found_target_skus = set()

        for i, url in enumerate(urls):
            sku = self._extract_sku_from_url(url)

            position_data = {
                'sku': sku,
                'url': url,
                'position': i + 1
            }

            found_positions.append(position_data)
            if sku:
                found_target_skus.add(sku)

            logger.debug(f"Товар номер {i + 1}: {url}")

            if find_skus and all(
                    target_sku in found_target_skus for target_sku in
                    find_skus):
                logger.debug(f"Все искомые ску найдены: {find_skus}")
                break

        self.found_positions = found_positions
        return found_positions

    def _extract_sku_from_url(self, url: str) -> Optional[int]:
        if '/product/' not in url:
            return None

        try:
            product_part = url.split('/product/')[-1].split('?')[0]
            sku_match = re.findall(r'\d+', product_part)
            if sku_match:
                return int(sku_match[-1])
        except (ValueError, IndexError):
            pass

        return None

    async def get_product_by_sku(self, sku: int) -> Optional[Dict]:
        for position in self.found_positions:
            if position['sku'] == sku:
                return position
        return None