import pytest
from datetime import date
from decimal import Decimal
from market_data.models import Brand, SubBrand, Product, Market, Data


@pytest.fixture
def data_record(db):
    brand = Brand.objects.create(description="UT PLUS")
    subbrand = SubBrand.objects.create(description="UT VETO BRETS", brand=brand)
    product = Product.objects.create(
        description="CHS ORGANIC TREE UT PLUS UT VETO BRETS FAMILY 400",
        sub_brand=subbrand,
    )
    market = Market.objects.create(description="MARKET3", description_2="TOT RETAILER 1")
    return Data.objects.create(
        market=market,
        product=product,
        value=Decimal("32.40"),
        weighted_distribution=Decimal("85.85"),
        date=date(2016, 9, 4),
        period_weeks=4,
    )


@pytest.mark.django_db
def test_brand_can_be_created():
    brand = Brand.objects.create(description="UT PLUS")
    assert brand.id is not None
    assert brand.description == "UT PLUS"


@pytest.mark.django_db
def test_subbrand_belongs_to_brand():
    brand = Brand.objects.create(description="UT PLUS")
    subbrand = SubBrand.objects.create(description="UT VETO BRETS", brand=brand)
    assert subbrand.brand_id == brand.id


@pytest.mark.django_db
def test_subbrand_cascades_on_brand_delete():
    brand = Brand.objects.create(description="UT PLUS")
    subbrand = SubBrand.objects.create(description="UT VETO BRETS", brand=brand)
    brand.delete()
    assert not SubBrand.objects.filter(id=subbrand.id).exists()


@pytest.mark.django_db
def test_product_belongs_to_subbrand():
    brand = Brand.objects.create(description="UT PLUS")
    subbrand = SubBrand.objects.create(description="UT VETO BRETS", brand=brand)
    product = Product.objects.create(
        description="CHS ORGANIC TREE UT PLUS UT VETO BRETS FAMILY 400",
        sub_brand=subbrand,
    )
    assert product.sub_brand_id == subbrand.id


@pytest.mark.django_db
def test_product_cascades_on_subbrand_delete():
    brand = Brand.objects.create(description="UT PLUS")
    subbrand = SubBrand.objects.create(description="UT VETO BRETS", brand=brand)
    product = Product.objects.create(
        description="CHS ORGANIC TREE UT PLUS UT VETO BRETS FAMILY 400",
        sub_brand=subbrand,
    )
    subbrand.delete()
    assert not Product.objects.filter(id=product.id).exists()


@pytest.mark.django_db
def test_market_can_be_created():
    market = Market.objects.create(description="MARKET3", description_2="TOT RETAILER 1")
    assert market.id is not None
    assert market.description == "MARKET3"
    assert market.description_2 == "TOT RETAILER 1"


def test_data_links_market_and_product(data_record):
    assert data_record.id is not None
    assert data_record.value == Decimal("32.40")
    assert data_record.weighted_distribution == Decimal("85.85")
    assert data_record.period_weeks == 4
    assert data_record.market_id == data_record.market.id
    assert data_record.product_id == data_record.product.id
    assert data_record.date == date(2016, 9, 4)


def test_data_cascades_on_market_delete(data_record):
    data_id = data_record.id
    data_record.market.delete()
    assert not Data.objects.filter(id=data_id).exists()


def test_data_cascades_on_product_delete(data_record):
    data_id = data_record.id
    data_record.product.delete()
    assert not Data.objects.filter(id=data_id).exists()


@pytest.mark.django_db
def test_data_weighted_distribution_can_be_null():
    brand = Brand.objects.create(description="BRAND X")
    subbrand = SubBrand.objects.create(description="SUBBRAND X", brand=brand)
    product = Product.objects.create(description="PRODUCT X", sub_brand=subbrand)
    market = Market.objects.create(description="MARKET X", description_2="RETAILER X")
    data = Data.objects.create(
        market=market,
        product=product,
        value=Decimal("100.00"),
        weighted_distribution=None,
        date=date(2016, 9, 4),
        period_weeks=4,
    )
    data.refresh_from_db()
    assert data.weighted_distribution is None
