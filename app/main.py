from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    _ROOT = Path(__file__).resolve().parents[1]
    load_dotenv(_ROOT / ".env")
except ImportError:
    pass

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from pymysql.err import IntegrityError

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from app.resources.CustomerResource import (
        Customer,
        CustomerCollection,
        CustomerResource,
    )
    from app.resources.HarryPotterResource import (
        HarryPotterCharacter,
        HarryPotterCollection,
        HarryPotterResource,
    )
    from app.resources.OrderDetailsResource import (
        OrderDetail,
        OrderDetailCollection,
        OrderDetailsResource,
    )
    from app.resources.OrderResource import Order, OrderCollection, OrderResource
else:
    from .resources.CustomerResource import (
        Customer,
        CustomerCollection,
        CustomerResource,
    )
    from .resources.HarryPotterResource import (
        HarryPotterCharacter,
        HarryPotterCollection,
        HarryPotterResource,
    )
    from .resources.OrderDetailsResource import (
        OrderDetail,
        OrderDetailCollection,
        OrderDetailsResource,
    )
    from .resources.OrderResource import Order, OrderCollection, OrderResource


def _get_app_name() -> str:
    return os.getenv("APP_NAME", "Starter FastAPI App")


def _query_template(request: Request) -> dict:
    return {k: v for k, v in request.query_params.items() if v != ""}


def _order_detail_pk(order_number: int, product_code: str) -> str:
    return f"{order_number}|{product_code}"


app = FastAPI(title=_get_app_name(), version="0.1.0")

harry_potter_resource = HarryPotterResource()
customer_resource = CustomerResource()
order_resource = OrderResource()
order_details_resource = OrderDetailsResource()


class EchoRequest(BaseModel):
    message: str


@app.get("/", tags=["root"])
def read_root() -> dict[str, str]:
    return {"message": "Hello from FastAPI"}


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/echo", tags=["echo"])
def echo(payload: EchoRequest) -> EchoRequest:
    return payload


# --- Customers ---


@app.get("/customers", tags=["customers"])
def list_customers(request: Request) -> CustomerCollection:
    return customer_resource.get(_query_template(request))


@app.post("/customers", tags=["customers"])
def create_customer(new_data: Customer) -> str:
    try:
        return customer_resource.post(new_data)
    except IntegrityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/customers/{customerNumber}", tags=["customers"])
def get_customer(customerNumber: int) -> Customer:
    try:
        return customer_resource.get_by_id(str(customerNumber))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.put("/customers/{customerNumber}", tags=["customers"])
def update_customer(customerNumber: int, new_data: Customer) -> dict[str, int]:
    try:
        updated = customer_resource.put(str(customerNumber), new_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"updated": updated}


@app.delete("/customers/{customerNumber}", tags=["customers"])
def delete_customer(customerNumber: int) -> dict[str, int]:
    try:
        deleted = customer_resource.delete(str(customerNumber))
    except IntegrityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"deleted": deleted}


# --- Orders ---


@app.get("/orders", tags=["orders"])
def list_orders(request: Request) -> OrderCollection:
    return order_resource.get(_query_template(request))


@app.post("/orders", tags=["orders"])
def create_order(new_data: Order) -> str:
    try:
        return order_resource.post(new_data)
    except IntegrityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/orders/{orderNumber}", tags=["orders"])
def get_order(orderNumber: int) -> Order:
    try:
        return order_resource.get_by_id(str(orderNumber))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.put("/orders/{orderNumber}", tags=["orders"])
def update_order(orderNumber: int, new_data: Order) -> dict[str, int]:
    try:
        updated = order_resource.put(str(orderNumber), new_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"updated": updated}


@app.delete("/orders/{orderNumber}", tags=["orders"])
def delete_order(orderNumber: int) -> dict[str, int]:
    try:
        deleted = order_resource.delete(str(orderNumber))
    except IntegrityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"deleted": deleted}


# --- Order details ---


@app.get("/orderdetails", tags=["orderdetails"])
def list_order_details(request: Request) -> OrderDetailCollection:
    return order_details_resource.get(_query_template(request))


@app.post("/orderdetails", tags=["orderdetails"])
def create_order_detail(new_data: OrderDetail) -> str:
    try:
        return order_details_resource.post(new_data)
    except (IntegrityError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/orders/{orderNumber}/orderdetails", tags=["orderdetails"])
def list_order_details_for_order(orderNumber: int) -> OrderDetailCollection:
    return order_details_resource.get({"orderNumber": str(orderNumber)})


@app.get(
    "/orders/{orderNumber}/orderdetails/{productCode}",
    tags=["orderdetails"],
)
def get_order_detail(orderNumber: int, productCode: str) -> OrderDetail:
    try:
        return order_details_resource.get_by_id(_order_detail_pk(orderNumber, productCode))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.put(
    "/orders/{orderNumber}/orderdetails/{productCode}",
    tags=["orderdetails"],
)
def update_order_detail(
    orderNumber: int, productCode: str, new_data: OrderDetail
) -> dict[str, int]:
    try:
        updated = order_details_resource.put(
            _order_detail_pk(orderNumber, productCode), new_data
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"updated": updated}


@app.delete(
    "/orders/{orderNumber}/orderdetails/{productCode}",
    tags=["orderdetails"],
)
def delete_order_detail(orderNumber: int, productCode: str) -> dict[str, int]:
    try:
        deleted = order_details_resource.delete(_order_detail_pk(orderNumber, productCode))
    except IntegrityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"deleted": deleted}


# --- Harry Potter (starter sample) ---


@app.get("/harry-potter", tags=["harry-potter"])
def get_harry_potter_characters(
    first_name: str | None = None,
    last_name: str | None = None,
    house_name: str | None = None,
) -> HarryPotterCollection:
    template: dict = {}
    if first_name is not None:
        template["first_name"] = first_name
    if last_name is not None:
        template["last_name"] = last_name
    if house_name is not None:
        template["house_name"] = house_name
    return harry_potter_resource.get(template)


@app.get("/harry-potter/{character_id}", tags=["harry-potter"])
def get_harry_potter_character_by_id(character_id: str) -> HarryPotterCharacter:
    try:
        return harry_potter_resource.get_by_id(character_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/harry-potter", tags=["harry-potter"])
def create_harry_potter_character(new_data: HarryPotterCharacter) -> str:
    new_id = harry_potter_resource.post(new_data)
    return str(new_id)


@app.put("/harry-potter/{character_id}", tags=["harry-potter"])
def update_harry_potter_character(
    character_id: str, new_data: HarryPotterCharacter
) -> dict[str, int]:
    try:
        updated = harry_potter_resource.put(character_id, new_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"updated": updated}


@app.delete("/harry-potter/{character_id}", tags=["harry-potter"])
def delete_harry_potter_character(character_id: str) -> dict[str, int]:
    deleted = harry_potter_resource.delete(character_id)
    return {"deleted": deleted}


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    uvicorn.run(app, host=host, port=port)
