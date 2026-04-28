import datetime
import pytest
from decimal import Decimal
from rest_framework.test import APIClient
from market_data.models import Brand, SubBrand, Product, Market, Data


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def market(db):
    return Market.objects.create(description='MARKET1', description_2='TOT RETAILER 1')


def _make_brand(brand_name, sub_name, product_name, market, rows):
    """rows: list of (value, wtd_or_none, date) tuples."""
    brand, _ = Brand.objects.get_or_create(description=brand_name)
    sub, _ = SubBrand.objects.get_or_create(description=sub_name, brand=brand)
    product, _ = Product.objects.get_or_create(description=product_name, sub_brand=sub)
    for value, wtd, date in rows:
        Data.objects.create(
            market=market,
            product=product,
            value=Decimal(str(value)),
            weighted_distribution=Decimal(str(wtd)) if wtd is not None else None,
            date=date,
            period_weeks=4,
        )
    return brand


@pytest.mark.django_db
def test_happy_path(api_client, market):
    # weighted avg WTD = (1000*40 + 3000*60) / (1000+3000) = 220000/4000 = 55.00
    _make_brand('BRAND A', 'SUB A', 'PROD A', market, [
        (1000, 40, datetime.date(2016, 9, 4)),
        (3000, 60, datetime.date(2016, 9, 11)),
    ])

    response = api_client.get('/market-data/dominance/')

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]['brand'] == 'BRAND A'
    assert Decimal(data[0]['total_value']) == Decimal('4000')
    assert Decimal(data[0]['weighted_avg_wtd']) == Decimal('55.00')


@pytest.mark.django_db
def test_all_null_wtd_returns_null(api_client, market):
    _make_brand('BRAND NULL', 'SUB N', 'PROD N', market, [
        (1000, None, datetime.date(2016, 9, 4)),
        (2000, None, datetime.date(2016, 9, 11)),
    ])

    response = api_client.get('/market-data/dominance/')

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]['weighted_avg_wtd'] is None


@pytest.mark.django_db
def test_mixed_null_wtd_uses_only_non_null_rows(api_client, market):
    # Only the non-null row contributes to the weighted average: (2000*60) / 2000 = 60.00
    _make_brand('BRAND MIX', 'SUB M', 'PROD M', market, [
        (1000, None, datetime.date(2016, 9, 4)),
        (2000, 60, datetime.date(2016, 9, 11)),
    ])

    response = api_client.get('/market-data/dominance/')

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert Decimal(data[0]['weighted_avg_wtd']) == Decimal('60.00')


@pytest.mark.django_db
def test_ordered_by_total_value_descending(api_client, market):
    _make_brand('SMALL', 'SUB S', 'PROD S', market, [(500, 30, datetime.date(2016, 9, 4))])
    _make_brand('BIG', 'SUB B', 'PROD B', market, [(9000, 70, datetime.date(2016, 9, 4))])

    response = api_client.get('/market-data/dominance/')

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]['brand'] == 'BIG'
    assert data[1]['brand'] == 'SMALL'
