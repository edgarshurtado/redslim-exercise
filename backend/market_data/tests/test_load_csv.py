import io
import pytest
from pathlib import Path
from django.core.management import call_command
from market_data.models import Brand, SubBrand, Product, Market, Data

CSV_HEADER = "M Desc,VAL,WTD,Product,LEVEL,CATEGORY,MANUFACTURER,BRAND,SUBBRAND,SEGMENT,PACKSIZE,SIZE,FORMAT,TIME,M Desc 2,DATETIME"

ROW_1 = "MARKET3,1000,9400,CHS ORGANIC TREE UT PLUS UT VETO BRETS FAMILY 400,ITEM,CHS,ORGANIC TREE,UT PLUS,UT VETO BRETS,FAMILY,400-499G,400.0,CHUNKY,AUG16 4WKS 04/09/16,TOT RETAILER 1,2016-09-04"
ROW_2 = "MARKET3,2000,8500,CHS SUPER FOOD SON WIIT-PEX CAYNTGAWN ADULT 500,ITEM,CHS,SUPER FOOD,SON WIIT-PEX,CAYNTGAWN,ADULT,500-599G,500.0,SHREDDED/GRATED,AUG16 4WKS 04/09/16,TOT RETAILER 2,2016-09-04"
ROW_3 = "MARKET4,3000,7500,CHS PRIVATE LABEL PL-SUB FAMILY 300,ITEM,CHS,PRIVATE LABEL,PRIVATE LABEL,PL-SUB,FAMILY,300-399G,300.0,CHUNKY,AUG16 4WKS 04/09/16,TOT RETAILER 1,2016-09-04"


@pytest.fixture
def data_dir():
    path = Path(__file__).resolve().parents[3] / "docs" / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture
def write_csv(data_dir):
    written = []

    def _write(filename, content):
        (data_dir / filename).write_text(content)
        written.append(data_dir / filename)
        return filename

    yield _write

    for p in written:
        p.unlink(missing_ok=True)


@pytest.mark.django_db
def test_happy_path(write_csv):
    filename = write_csv("test_happy.csv", "\n".join([CSV_HEADER, ROW_1, ROW_2, ROW_3]))

    out = io.StringIO()
    call_command("load_csv", filename, stdout=out)

    assert Brand.objects.count() == 3
    assert SubBrand.objects.count() == 3
    assert Product.objects.count() == 3
    assert Market.objects.count() == 3
    assert Data.objects.count() == 3

    data_row = Data.objects.get(
        product__description="CHS ORGANIC TREE UT PLUS UT VETO BRETS FAMILY 400"
    )
    assert data_row.value == 1000
    assert data_row.weighted_distribution == 9400
    assert str(data_row.date) == "2016-09-04"
    assert data_row.period_weeks == 4
    assert "Loaded 3 rows from test_happy.csv." in out.getvalue()


@pytest.mark.django_db
def test_idempotency(write_csv):
    filename = write_csv("test_idempotent.csv", "\n".join([CSV_HEADER, ROW_1, ROW_2, ROW_3]))

    call_command("load_csv", filename)
    call_command("load_csv", filename)

    assert Brand.objects.count() == 3
    assert SubBrand.objects.count() == 3
    assert Product.objects.count() == 3
    assert Market.objects.count() == 3
    assert Data.objects.count() == 3


@pytest.mark.django_db
def test_dimension_deduplication(write_csv):
    row_a = "MARKET3,1000,9400,PRODUCT ALPHA,ITEM,CHS,MFG,SHARED BRAND,SHARED SUB,FAMILY,400-499G,400.0,CHUNKY,AUG16 4WKS 04/09/16,TOT RETAILER 1,2016-09-04"
    row_b = "MARKET3,2000,8500,PRODUCT BETA,ITEM,CHS,MFG,SHARED BRAND,SHARED SUB,ADULT,400-499G,400.0,CHUNKY,AUG16 4WKS 11/09/16,TOT RETAILER 1,2016-09-11"

    filename = write_csv("test_dedup.csv", "\n".join([CSV_HEADER, row_a, row_b]))
    call_command("load_csv", filename)

    assert Brand.objects.filter(description="SHARED BRAND").count() == 1
    assert SubBrand.objects.filter(description="SHARED SUB").count() == 1
    assert Product.objects.count() == 2
    assert Data.objects.count() == 2
