from __future__ import annotations

from pydantic import BaseModel, Field

from .AbstractBaseResource import AbstractBaseResource
from ..services.MySQLDataService import MySQLDataService, load_mysql_env


class OrderDetail(BaseModel):
    orderNumber: int
    productCode: str = ""
    quantityOrdered: int = 0
    priceEach: float = 0.0
    orderLineNumber: int = 0


class OrderDetailCollection(BaseModel):
    items: list[OrderDetail] = Field(default_factory=list)


class OrderDetailsResource(AbstractBaseResource):
    """Composite primary key (orderNumber, productCode) encoded as ``"{orderNumber}|{productCode}"``."""

    def __init__(self, config: dict | None = None) -> None:
        cfg = dict(config or {})
        super().__init__(cfg)
        base = load_mysql_env()
        base.update(cfg)
        service_config = {
            **base,
            "table": "orderdetails",
            "primary_key_columns": ["orderNumber", "productCode"],
            "integer_columns": ["orderNumber", "quantityOrdered", "orderLineNumber"],
            "float_columns": ["priceEach"],
            "auto_increment_pk": False,
        }
        self._service = MySQLDataService(service_config)

    def get(self, template: dict) -> OrderDetailCollection:
        rows = self._service.retrieveByTemplate(template)
        return OrderDetailCollection(items=[OrderDetail.model_validate(r) for r in rows])

    def get_by_id(self, id: str) -> OrderDetail:  # noqa: A002
        row = self._service.retrieveByPrimaryKey(str(id))
        if not row:
            raise ValueError(f"No order detail with key {id!r}")
        return OrderDetail.model_validate(row)

    def post(self, new_data: OrderDetail) -> str:
        data = new_data.model_dump(exclude_none=True, mode="json")
        return self._service.create(data)

    def delete(self, id: str) -> int:  # noqa: A002
        return self._service.deleteByPrimaryKey(str(id))

    def put(self, character_id: str, new_data: OrderDetail) -> int:
        existing = self._service.retrieveByPrimaryKey(str(character_id))
        if not existing:
            raise ValueError(f"No order detail with key {character_id!r}")
        incoming = new_data.model_dump(exclude_none=True, mode="json")
        merged = {**existing, **incoming}
        parts = character_id.split("|", 1)
        merged["orderNumber"] = int(parts[0])
        merged["productCode"] = parts[1]
        return self._service.updateByPrimaryKey(str(character_id), merged)
