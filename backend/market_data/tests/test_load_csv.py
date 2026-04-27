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

    out = io.StringIO()
    call_command("load_csv", filename, stdout=out)
    call_command("load_csv", filename)

    assert "Loaded 3 rows from test_idempotent.csv." in out.getvalue()
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
    assert Market.objects.count() == 1
    assert Product.objects.count() == 2
    assert Data.objects.count() == 2


@pytest.mark.django_db
def test_cache_effectiveness(write_csv):
    """Dimension caches prevent repeated DB queries for duplicate dimension values."""
    dates = [
        ("AUG16 4WKS 04/09/16", "2016-09-04"),
        ("AUG16 4WKS 11/09/16", "2016-09-11"),
        ("AUG16 4WKS 18/09/16", "2016-09-18"),
        ("AUG16 4WKS 25/09/16", "2016-09-25"),
        ("SEP16 4WKS 02/10/16", "2016-10-02"),
        ("SEP16 4WKS 09/10/16", "2016-10-09"),
        ("SEP16 4WKS 16/10/16", "2016-10-16"),
        ("SEP16 4WKS 23/10/16", "2016-10-23"),
        ("SEP16 4WKS 30/10/16", "2016-10-30"),
        ("OCT16 4WKS 06/11/16", "2016-11-06"),
    ]
    N = len(dates)
    rows = [
        f"MARKET3,1000,9400,SAME PRODUCT,ITEM,CHS,MFG,SAME BRAND,SAME SUB,FAMILY,400-499G,400.0,CHUNKY,{time},TOT RETAILER 1,{iso}"
        for time, iso in dates
    ]
    filename = write_csv("test_cache.csv", "\n".join([CSV_HEADER] + rows))

    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    with CaptureQueriesContext(connection) as ctx:
        call_command("load_csv", filename)

    # Filter out SAVEPOINT statements (transaction infrastructure, not data queries).
    data_queries = [q for q in ctx.captured_queries if "SAVEPOINT" not in q["sql"]]

    # With caching: 4 dims × 2 queries (SELECT+INSERT, first row only) + N data × 2 = 8 + 2N = 28
    # Without caching: 4 dims × 2 per row + N data × 2 = 8N + 2N = ~64 for N=10
    # N * 4 = 40, so 28 < 40 passes and 64 > 40 would fail (catching missing cache)
    assert len(data_queries) < N * 4
