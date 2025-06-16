import os
import sys
import importlib.util
from pathlib import Path
from datetime import datetime

import pytest

ROOT = Path(__file__).resolve().parents[1]
db_path = ROOT / "core" / "database.py"
spec = importlib.util.spec_from_file_location("database", db_path)
database = importlib.util.module_from_spec(spec)
spec.loader.exec_module(database)

DatabaseManager = database.DatabaseManager
Customer = database.Customer
Product = database.Product
Quotation = database.Quotation
Sale = database.Sale
Receivable = database.Receivable

@pytest.fixture
def db():
    manager = DatabaseManager(db_path=':memory:')
    yield manager
    manager.close_session()

def test_crud_operations(db):
    customer = Customer(name='Test Customer')
    db.create(customer)
    assert customer.id is not None

    fetched = db.read(Customer, id=customer.id)
    assert fetched and fetched[0].name == 'Test Customer'

    db.update(customer, name='Updated Customer')
    assert db.read(Customer, id=customer.id)[0].name == 'Updated Customer'

    assert db.delete(customer)
    assert db.read(Customer, id=customer.id) == []

def test_new_models(db):
    customer = Customer(name='Alice')
    product = Product(name='Widget')
    db.create(customer)
    db.create(product)

    quotation = Quotation(
        quotation_date=datetime.utcnow(),
        customer=customer,
        total_amount=100.0,
    )
    db.create(quotation)

    sale = Sale(
        sale_date=datetime.utcnow(),
        customer=customer,
        product=product,
        quantity=2,
        unit_price=50.0,
        total_amount=100.0,
    )
    db.create(sale)

    receivable = Receivable(
        customer=customer,
        amount_due=100.0,
        due_date=datetime.utcnow(),
    )
    db.create(receivable)

    assert quotation in customer.quotations
    assert sale in product.sales
    assert receivable in customer.receivables
