from __future__ import annotations

from pydantic import BaseModel, Field

from .AbstractBaseResource import AbstractBaseResource
from ..services.MySQLDataService import MySQLDataService, load_mysql_env


class Customer(BaseModel):
    customerNumber: int | None = None
    customerName: str = ""
    contactLastName: str = ""
    contactFirstName: str = ""
    phone: str = ""
    addressLine1: str = ""
    addressLine2: str | None = None
    city: str = ""
    state: str | None = None
    postalCode: str | None = None
    country: str = ""
    salesRepEmployeeNumber: int | None = None
    creditLimit: float | None = None


class CustomerCollection(BaseModel):
    items: list[Customer] = Field(default_factory=list)


class CustomerResource(AbstractBaseResource):
    def __init__(self, config: dict | None = None) -> None:
        cfg = dict(config or {})
        super().__init__(cfg)
        base = load_mysql_env()
        base.update(cfg)
        service_config = {
            **base,
            "table": "customers",
            "primary_key_columns": ["customerNumber"],
            "integer_columns": ["customerNumber", "salesRepEmployeeNumber"],
            "float_columns": ["creditLimit"],
            "auto_increment_pk": True,
        }
        self._service = MySQLDataService(service_config)

    def get(self, template: dict) -> CustomerCollection:
        rows = self._service.retrieveByTemplate(template)
        return CustomerCollection(items=[Customer.model_validate(r) for r in rows])

    def get_by_id(self, id: str) -> Customer:  # noqa: A002
        row = self._service.retrieveByPrimaryKey(str(id))
        if not row:
            raise ValueError(f"No customer with customerNumber {id!r}")
        return Customer.model_validate(row)

    def post(self, new_data: Customer) -> str:
        data = new_data.model_dump(exclude_none=True)
        if data.get("customerNumber") is None:
            data.pop("customerNumber", None)
        return self._service.create(data)

    def delete(self, id: str) -> int:  # noqa: A002
        return self._service.deleteByPrimaryKey(str(id))

    def put(self, character_id: str, new_data: Customer) -> int:
        existing = self._service.retrieveByPrimaryKey(str(character_id))
        if not existing:
            raise ValueError(f"No customer with customerNumber {character_id!r}")
        merged = {**existing, **new_data.model_dump(exclude_none=True)}
        merged["customerNumber"] = int(character_id)
        return self._service.updateByPrimaryKey(str(character_id), merged)
