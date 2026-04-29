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
    body = response.json()
    assert body['results'] == ['ALPHA', 'ZEBRA']
    assert body['count'] == 2
    assert body['next'] is None
    assert body['previous'] is None


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
    assert response.json()['results'] == ['PROD A', 'PROD Z']


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
    assert response.json()['results'] == ['MARKET A', 'MARKET B']


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
    assert response.json()['results'] == ['REAL BRAND']


@pytest.mark.django_db
def test_options_missing_category_param_returns_400(api_client):
    response = api_client.get('/market-data/evolution/options/')
    assert response.status_code == 400


@pytest.mark.django_db
def test_options_first_page_returns_50_items_and_next_link(api_client, market):
    for i in range(60):
        _make_brand_data(f'BRAND {i:03d}', market)

    response = api_client.get('/market-data/evolution/options/?category=brand')

    assert response.status_code == 200
    body = response.json()
    assert body['count'] == 60
    assert len(body['results']) == 50
    assert body['results'][0] == 'BRAND 000'
    assert body['results'][-1] == 'BRAND 049'
    assert body['next'] is not None
    assert 'page=2' in body['next']


@pytest.mark.django_db
def test_options_second_page_returns_remaining_items(api_client, market):
    for i in range(60):
        _make_brand_data(f'BRAND {i:03d}', market)

    response = api_client.get('/market-data/evolution/options/?category=brand&page=2')

    assert response.status_code == 200
    body = response.json()
    assert len(body['results']) == 10
    assert body['results'][0] == 'BRAND 050'
    assert body['results'][-1] == 'BRAND 059'
    assert body['next'] is None
    assert body['previous'] is not None


@pytest.mark.django_db
def test_chart_aggregates_value_by_calendar_year(api_client, market):
    brand, _ = Brand.objects.get_or_create(description='BRD A')
    sub, _ = SubBrand.objects.get_or_create(description='SUB A', brand=brand)
    product, _ = Product.objects.get_or_create(description='PROD A', sub_brand=sub)
    Data.objects.create(market=market, product=product, value=Decimal('1000'),
                        date=datetime.date(2020, 3, 1), period_weeks=4)
    Data.objects.create(market=market, product=product, value=Decimal('2000'),
                        date=datetime.date(2020, 9, 1), period_weeks=4)
    Data.objects.create(market=market, product=product, value=Decimal('3000'),
                        date=datetime.date(2021, 1, 1), period_weeks=4)

    response = api_client.get('/market-data/evolution/chart/?category=brand&value=BRD A')

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0] == {'year': 2020, 'total': '3000.00'}
    assert data[1] == {'year': 2021, 'total': '3000.00'}


@pytest.mark.django_db
def test_chart_results_sorted_ascending_by_year(api_client, market):
    brand, _ = Brand.objects.get_or_create(description='BRD B')
    sub, _ = SubBrand.objects.get_or_create(description='SUB B', brand=brand)
    product, _ = Product.objects.get_or_create(description='PROD B', sub_brand=sub)
    Data.objects.create(market=market, product=product, value=Decimal('500'),
                        date=datetime.date(2022, 1, 1), period_weeks=4)
    Data.objects.create(market=market, product=product, value=Decimal('100'),
                        date=datetime.date(2019, 1, 1), period_weeks=4)

    response = api_client.get('/market-data/evolution/chart/?category=brand&value=BRD B')

    assert response.status_code == 200
    data = response.json()
    assert data[0]['year'] == 2019
    assert data[1]['year'] == 2022


@pytest.mark.django_db
def test_chart_missing_value_param_returns_400(api_client):
    response = api_client.get('/market-data/evolution/chart/?category=brand')
    assert response.status_code == 400


@pytest.mark.django_db
def test_chart_unknown_category_returns_400(api_client):
    response = api_client.get('/market-data/evolution/chart/?category=foo&value=bar')
    assert response.status_code == 400


@pytest.mark.django_db
def test_chart_excludes_rows_with_empty_brand(api_client, market):
    real_brand, _ = Brand.objects.get_or_create(description='REAL')
    empty_brand, _ = Brand.objects.get_or_create(description='')
    for brand_obj, prod_name in [(real_brand, 'PROD R'), (empty_brand, 'PROD E')]:
        sub, _ = SubBrand.objects.get_or_create(description=f'SUB_{prod_name}', brand=brand_obj)
        product, _ = Product.objects.get_or_create(description=prod_name, sub_brand=sub)
        Data.objects.create(market=market, product=product, value=Decimal('1000'),
                            date=datetime.date(2020, 1, 1), period_weeks=4)

    response = api_client.get('/market-data/evolution/chart/?category=brand&value=REAL')

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert Decimal(data[0]['total']) == Decimal('1000')
