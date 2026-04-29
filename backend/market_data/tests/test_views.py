import pytest
from datetime import date, timedelta
from decimal import Decimal
from rest_framework.test import APIClient
from market_data.models import Brand, SubBrand, Product, Market, Data

TABLE_URL = '/market-data/table/'


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def two_records(db):
    brand = Brand.objects.create(description="Brand")
    subbrand = SubBrand.objects.create(description="Sub", brand=brand)
    product = Product.objects.create(description="Product", sub_brand=subbrand)
    market_a = Market.objects.create(description="AAA", description_2="R1")
    market_z = Market.objects.create(description="ZZZ", description_2="R2")
    d1 = Data.objects.create(
        market=market_a, product=product,
        value=Decimal("10.00"), date=date(2022, 1, 1), period_weeks=4,
    )
    d2 = Data.objects.create(
        market=market_z, product=product,
        value=Decimal("20.00"), date=date(2023, 6, 1), period_weeks=4,
        weighted_distribution=Decimal("75.50"),
    )
    return d1, d2


@pytest.fixture
def fifty_one_records(db):
    brand = Brand.objects.create(description="Brand")
    subbrand = SubBrand.objects.create(description="Sub", brand=brand)
    product = Product.objects.create(description="Product", sub_brand=subbrand)
    market = Market.objects.create(description="Market", description_2="Retailer")
    Data.objects.bulk_create([
        Data(
            market=market, product=product,
            value=Decimal("1.00"),
            date=date(2020, 1, 1) + timedelta(days=i),
            period_weeks=4,
        )
        for i in range(51)
    ])


@pytest.mark.django_db
def test_default_response_shape(api_client, two_records):
    response = api_client.get(TABLE_URL)
    assert response.status_code == 200
    results = response.data['results']
    assert len(results) == 2
    row = results[0]
    assert set(row.keys()) == {
        'id', 'market', 'product', 'brand', 'sub_brand',
        'value', 'date', 'period_weeks', 'weighted_distribution',
    }
    assert row['market'] == 'ZZZ'
    assert row['product'] == 'Product'
    assert row['brand'] == 'Brand'
    assert row['sub_brand'] == 'Sub'
    assert str(row['weighted_distribution']) == '75.50'


@pytest.mark.django_db
def test_default_ordering_is_date_descending(api_client, two_records):
    response = api_client.get(TABLE_URL)
    results = response.data['results']
    assert str(results[0]['date']) == '2023-06-01'
    assert str(results[1]['date']) == '2022-01-01'


@pytest.mark.django_db
def test_ordering_by_market_ascending(api_client, two_records):
    response = api_client.get(TABLE_URL + '?ordering=market')
    results = response.data['results']
    assert results[0]['market'] == 'AAA'
    assert results[1]['market'] == 'ZZZ'


@pytest.mark.django_db
def test_ordering_by_value_descending(api_client, two_records):
    response = api_client.get(TABLE_URL + '?ordering=-value')
    results = response.data['results']
    assert Decimal(results[0]['value']) == Decimal("20.00")
    assert Decimal(results[1]['value']) == Decimal("10.00")


@pytest.mark.django_db
def test_pagination_page_size_is_50(api_client, fifty_one_records):
    response = api_client.get(TABLE_URL)
    assert response.status_code == 200
    assert len(response.data['results']) == 50


@pytest.mark.django_db
def test_pagination_page_2_returns_remaining_record(api_client, fifty_one_records):
    response = api_client.get(TABLE_URL + '?page=2')
    assert response.status_code == 200
    assert len(response.data['results']) == 1


@pytest.mark.django_db
def test_pagination_response_envelope(api_client, fifty_one_records):
    response = api_client.get(TABLE_URL)
    assert response.data['count'] == 51
    assert response.data['next'] is not None
    assert response.data['previous'] is None
