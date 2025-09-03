import asyncio
from typing import Optional, List

from browser.browser_manager import launch_browser_context
from pages.search_page import OzonSearchPage
from pages.product_page import OzonProductPage
from models.query_params import OzSearchQueryParams
from utils.logger import setup_logger

logger = setup_logger()


class OzonPageManager:
    def __init__(self, context):
        self.context = context
        self.search_page: Optional[OzonSearchPage] = None
        self.product_page: Optional[OzonProductPage] = None

    async def initialize_search_page(self):
        page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        self.search_page = OzonSearchPage(page)
        return self.search_page

    async def initialize_product_page(self):
        page = await self.context.new_page()
        self.product_page = OzonProductPage(page)
        return self.product_page

    async def close(self):
        if self.product_page:
            await self.product_page.page.close()


async def oz_parse_and_add_to_basket_pom(
        query_params: OzSearchQueryParams,
        limit: int,
        find_skus: Optional[List[int]] = None,
        sku_to_add: Optional[int] = None,
        ):
    playwright, context = await launch_browser_context()
    page_manager = OzonPageManager(context)

    try:
        search_page = await page_manager.initialize_search_page()

        await search_page.search_by_query_params(query_params)

        product_urls = await search_page.scroll_to_load_more_products(limit)
        # logger.debug(f"Загружено URL товаров: {len(product_urls)}")

        found_positions = await search_page.extract_product_positions(
            product_urls, find_skus
        )
        logger.debug(f"Найдено товаров: {len(found_positions)}")

        for i, url in enumerate(found_positions):
            logger.debug(f"Товар номер {i + 1}: {url}")

        if sku_to_add:
            product_info = await search_page.get_product_by_sku(sku_to_add)

            if product_info:
                product_page = await page_manager.initialize_product_page()
                await product_page.navigate(product_info['url'])
                success = await product_page.add_to_basket()
                print(f"Товар успешно добавлен в корзину: {success}")
                print(f"Информация о добавленном товаре: ")
                print(f"Позиция в поиске: {product_info['position']}")
                print(f"SKU товара: {product_info['sku']}")
                print(f"URL товара: {product_info['url']}")
            else:
                print(f"Товар с SKU {sku_to_add} не найден")

        print("Нажмите на enter для закрытия браузера")
        await asyncio.get_event_loop().run_in_executor(None, input)

    finally:
        await page_manager.close()
        await context.close()
        await playwright.stop()


if __name__ == "__main__":
    query_params = OzSearchQueryParams(
        query="чай",
        # price_range=(100, 10000),
        # delivery=4
    )

    asyncio.run(
        oz_parse_and_add_to_basket_pom(
            query_params=query_params,
            limit=30,
            find_skus=[605006607, 1947128974],
            sku_to_add=605006607
        )
    )