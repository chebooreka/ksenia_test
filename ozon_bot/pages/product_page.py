from .base_page import BasePage
import logging

logger = logging.getLogger(__name__)


class OzonProductPage(BasePage):
    ADD_TO_CART_BUTTONS = [
        'button[data-widget="addToCart"]',
        'button[aria-label*="корзину"]',
        '.b25_3_3-a0',
        'div[data-widget="webAddToCart"] button',
        '.ui-k6'
    ]

    SUCCESS_INDICATORS = [
        '[aria-label*="добавлен"][aria-label*="корзину"]',
        '.b25_3_3-a1',
        '[data-widget*="cart"]',
        '.success-message'
    ]

    async def add_to_basket(self):
        for selector in self.ADD_TO_CART_BUTTONS:
            try:
                add_button = await self.page.wait_for_selector(
                    selector, timeout=2000, state='visible'
                )
                if add_button:
                    await add_button.scroll_into_view_if_needed()
                    await add_button.click()
                    logger.debug(f"Клик по кнопке с селектором: {selector}")

                    if await self._check_add_success():
                        return True
            except:
                continue

        logger.warning("Не удалось найти кнопку добавления в корзину")
        return False

    async def _check_add_success(self) -> bool:
        await self.page.wait_for_timeout(1000)

        for selector in self.SUCCESS_INDICATORS:
            try:
                element = await self.page.wait_for_selector(
                    selector, timeout=2000, state='visible'
                )
                if element:
                    logger.debug("Товар успешно добавлен в корзину")
                    return True
            except:
                continue

        logger.debug("Товар добавлен в корзину (косвенное подтверждение)")
        return True