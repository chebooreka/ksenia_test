import asyncio
import logging
from typing import Optional, List, Dict, ClassVar, Tuple
from urllib.parse import urlencode
import re

from pydantic import BaseModel
from playwright.async_api import async_playwright, BrowserContext

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)


class OzSearchQueryParams(BaseModel):
    base_url: ClassVar[str] = 'https://www.ozon.ru/search'
    query: str
    price_range: Optional[Tuple[int, int]] = None
    delivery: Optional[int] = None
    category: Optional[int] = None
    is_made_in_russia: Optional[bool] = None

    def to_query_string(self) -> str:
        params: Dict[str, str] = {"text": self.query}
        if self.price_range:
            low, high = self.price_range
            params["currency_price"] = f"{low:.3f};{high:.3f}"
        if self.delivery is not None:
            params["delivery"] = str(self.delivery)
        if self.category is not None:
            params["type"] = str(self.category)
        if self.is_made_in_russia:
            params["is_made_in_russia"] = "t"
        return self.base_url + "?" + urlencode(params)


class OzonPositionsBot:
    def __init__(self, context: BrowserContext, query_params: OzSearchQueryParams):
        self.context = context
        self.query_params = query_params

    async def get_positions(self, limit: int, find_skus: Optional[List[int]] = None, page=None):
        logger.debug("Ищем позиции товаров...")

        import random

        await page.mouse.wheel(0, random.randint(100, 500))
        await page.wait_for_timeout(random.randint(1000, 3000))

        if find_skus is None:
            find_skus = []

        close_page = False
        if page is None:
            page = await self.context.new_page()
            close_page = True

        search_url = self.query_params.to_query_string()
        await page.goto(search_url)
        await page.wait_for_timeout(5000)

        product_urls = await page.evaluate('''() => {
                const links = Array.from(document.querySelectorAll('a'));
                return links
                    .map(link => link.href)
                    .filter(href => href && href.includes('/product/'))
                    .filter((href, index, self) => self.indexOf(href) === index);
            }''')

        logger.debug(f"Найдено {len(product_urls)} продуктовых ссылок")

        found_positions = []
        found_target_skus = set()

        for i, url in enumerate(product_urls[:limit]):
            sku = None
            if '/product/' in url:
                product_part = url.split('/product/')[-1].split('?')[0]
                sku_match = re.findall(r'\d+', product_part)
                if sku_match:
                    sku = int(sku_match[-1])

            position_data = {
                'sku': sku,
                'url': url,
                'position': len(found_positions) + 1
            }

            found_positions.append(position_data)
            if sku:
                found_target_skus.add(sku)

            logger.debug(f"Продукт номер {i + 1}: {url}")

            if find_skus and all(
                    target_sku in found_target_skus for target_sku in
                    find_skus):
                logger.debug(f"все целевые SKU: {find_skus}")
                break

        logger.debug(f"{len(found_positions)} продуктов нашлось")

        if close_page:
            await page.close()

        return found_positions

    async def add_to_basket(self, sku_to_add: int, page=None):
        logger.debug(f"Добавляем в корзину по артикулам: {sku_to_add}")
        import random

        await page.mouse.wheel(0, random.randint(100, 500))
        await page.wait_for_timeout(random.randint(1000, 3000))

        close_page = False
        if page is None:
            page = await self.context.new_page()
            close_page = True

        try:
            product_urls = await page.evaluate('''() => {
                            const links = Array.from(document.querySelectorAll('a'));
                            return links
                                .map(link => link.href)
                                .filter(href => href && href.includes('/product/'))
                                .filter((href, index, self) => self.indexOf(href) === index);
                        }''')

            logger.debug(f"Найдено {len(product_urls)} продуктовых ссылок")

            import re
            target_index = -1
            for i, url in enumerate(product_urls):
                product_part = url.split('/product/')[-1].split('?')[0]
                sku_match = re.findall(r'\d+', product_part)
                if sku_match:
                    current_sku = int(sku_match[-1])
                    if current_sku == sku_to_add:
                        target_index = i
                        logger.debug(
                            f"Найден товар с SKU {sku_to_add} на позиции {i}")
                        break

            if target_index == -1:
                logger.warning(
                    f"Товар с SKU {sku_to_add} не найден на странице")
                await page.close()
                return False

            delivery_buttons = await page.query_selector_all(
                '.b25_3_3-a0')
            logger.debug(f"Найдено кнопок доставки: {len(delivery_buttons)}")
            if target_index < len(delivery_buttons):
                await delivery_buttons[target_index].click()
                await page.wait_for_timeout(3000)
                logger.debug("Клик по кнопке выполнен")

                try:
                    await page.wait_for_timeout(2000)

                    logger.debug(
                            "Товар добавлен в корзину")

                    await page.close()
                    return True

                except Exception as e:
                    logger.warning(f"Ошибка при подтверждении: {e}")
                    await page.close()
                    return True

            else:
                logger.warning(
                    f"Нет кнопки доставки для позиции {target_index}")
                if close_page:
                    await page.close()
                return True

        except Exception as e:
            logger.error(f"Ошибка добавления в корзину: {e}")
            await page.close()
            return False


async def launch_browser_context() -> tuple:
    playwright = await async_playwright().start()

    user_data_dir = "/users/chebooreka/playwright_profiles/ozon_profile"

    context: BrowserContext = await playwright.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        headless=False,
        locale="ru-RU",
        viewport={"width": 1280, "height": 800},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/119.0.0.0 Safari/537.36"
        ),
        args=[
            "--start-maximized",
            "--disable-blink-features=AutomationControlled"
        ],
    )

    return playwright, context


async def oz_parse_and_add_to_basket(
    query_params: OzSearchQueryParams,
    limit: int,
    find_skus: Optional[List[int]] = None,
    sku_to_add: Optional[int] = None,
):
    playwright, context = await launch_browser_context()
    try:
        bot = OzonPositionsBot(context, query_params)
        page = context.pages[0] if context.pages else await context.new_page()

        search_url = query_params.to_query_string()
        await page.goto(search_url)
        await page.wait_for_timeout(5000)

        result = await bot.get_positions(limit, find_skus, page=page)

        if sku_to_add:
            success = await bot.add_to_basket(sku_to_add, page=page)
            print(f"Товар добавлен в корзину: {success}")

        print("Нажмите на Enter, чтобы закрыть браузер...")
        await asyncio.get_event_loop().run_in_executor(None, input)

    finally:
        await context.close()
        await playwright.stop()


if __name__ == "__main__":
    query_params = OzSearchQueryParams(query="рыба",
    price_range=(100, 5000),
    delivery=2)

    asyncio.run(
        oz_parse_and_add_to_basket(
            query_params=query_params,
            limit=10,
            find_skus=[2166804538, 2490625498],
            sku_to_add=2166804538,
        )
    )
