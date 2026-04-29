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


def _make_brand_data(brand_name, market_obj, year=2020):
    brand, _ = Brand.objects.get_or_create(description=brand_name)
    sub, _ = SubBrand.objects.get_or_create(description=f'SUB_{brand_name}', brand=brand)
    product, _ = Product.objects.get_or_create(description=f'PROD_{brand_name}', sub_brand=sub)
    Data.objects.create(
        market=market_obj,
        product=product,
        value=Decimal('1000'),
        date=datetime.date(year, 1, 1),
        period_weeks=4,
    )


@pytest.mark.django_db
def test_options_brand_returns_sorted_list(api_client, market):
    _make_brand_data('ZEBRA', market)
    _make_brand_data('ALPHA', market)

    response = api_client.get('/market-data/evolution/options/?category=brand')

    assert response.status_code == 200
    assert response.json() == ['ALPHA', 'ZEBRA']


@pytest.mark.django_db
def test_options_product_returns_sorted_list(api_client, market):
    brand, _ = Brand.objects.get_or_create(description='BRD')
    for prod_name in ['PROD Z', 'PROD A']:
        sub, _ = SubBrand.objects.get_or_create(description=prod_name, brand=brand)
        product, _ = Product.objects.get_or_create(description=prod_name, sub_brand=sub)
        Data.objects.create(
            market=market, product=product, value=Decimal('100'),
            date=datetime.date(2020, 1, 1), period_weeks=4,
        )

    response = api_client.get('/market-data/evolution/options/?category=product')

    assert response.status_code == 200
    assert response.json() == ['PROD A', 'PROD Z']


@pytest.mark.django_db
def test_options_market_returns_sorted_list(api_client, db):
    brand, _ = Brand.objects.get_or_create(description='BRD')
    sub, _ = SubBrand.objects.get_or_create(description='SUB', brand=brand)
    product, _ = Product.objects.get_or_create(description='PROD', sub_brand=sub)
    for mkt_name in ['MARKET B', 'MARKET A']:
        m = Market.objects.create(description=mkt_name, description_2='')
        Data.objects.create(
            market=m, product=product, value=Decimal('100'),
            date=datetime.date(2020, 1, 1), period_weeks=4,
        )

    response = api_client.get('/market-data/evolution/options/?category=market')

    assert response.status_code == 200
    assert response.json() == ['MARKET A', 'MARKET B']


@pytest.mark.django_db
def test_options_unknown_category_returns_400(api_client):
    response = api_client.get('/market-data/evolution/options/?category=invalid')
    assert response.status_code == 400


@pytest.mark.django_db
def test_options_brand_excludes_empty_description(api_client, market):
    _make_brand_data('REAL BRAND', market)
    _make_brand_data('', market)

    response = api_client.get('/market-data/evolution/options/?category=brand')

    assert response.status_code == 200
    assert response.json() == ['REAL BRAND']
