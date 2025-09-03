from typing import Optional, List, Dict, ClassVar, Tuple
from urllib.parse import urlencode
from pydantic import BaseModel


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