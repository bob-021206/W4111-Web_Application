from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from .AbstractBaseResource import AbstractBaseResource
from ..services.MySQLDataService import MySQLDataService, load_mysql_env


class Order(BaseModel):
    orderNumber: int | None = None
    orderDate: date
    requiredDate: date
    shippedDate: date | None = None
    status: str = ""
    comments: str | None = None
    customerNumber: int


class OrderCollection(BaseModel):
    items: list[Order] = Field(default_factory=list)


class OrderResource(AbstractBaseResource):
    def __init__(self, config: dict | None = None) -> None:
        cfg = dict(config or {})
        super().__init__(cfg)
        base = load_mysql_env()
        base.update(cfg)
        service_config = {
            **base,
            "table": "orders",
            "primary_key_columns": ["orderNumber"],
            "integer_columns": ["orderNumber", "customerNumber"],
            "float_columns": [],
            "auto_increment_pk": True,
        }
        self._service = MySQLDataService(service_config)

    def get(self, template: dict) -> OrderCollection:
        rows = self._service.retrieveByTemplate(template)
        return OrderCollection(items=[Order.model_validate(r) for r in rows])

    def get_by_id(self, id: str) -> Order:  # noqa: A002
        row = self._service.retrieveByPrimaryKey(str(id))
        if not row:
            raise ValueError(f"No order with orderNumber {id!r}")
        return Order.model_validate(row)

    def post(self, new_data: Order) -> str:
        data = new_data.model_dump(exclude_none=True, mode="json")
        if data.get("orderNumber") is None:
            data.pop("orderNumber", None)
        return self._service.create(data)

    def delete(self, id: str) -> int:  # noqa: A002
        return self._service.deleteByPrimaryKey(str(id))

    def put(self, character_id: str, new_data: Order) -> int:
        existing = self._service.retrieveByPrimaryKey(str(character_id))
        if not existing:
            raise ValueError(f"No order with orderNumber {character_id!r}")
        merged = {**existing, **new_data.model_dump(exclude_none=True, mode="json")}
        merged["orderNumber"] = int(character_id)
        return self._service.updateByPrimaryKey(str(character_id), merged)
