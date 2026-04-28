import csv
import datetime
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from market_data.models import Brand, Data, Market, Product, SubBrand


class Command(BaseCommand):
    help = "Load retail sales data from a CSV file in docs/data/"

    def add_arguments(self, parser):
        parser.add_argument("filename", type=str, help="CSV file name in docs/data/")

    def handle(self, *args, **options):
        filename = options["filename"]
        csv_path = Path(__file__).resolve().parents[4] / "docs" / "data" / filename

        if not csv_path.exists():
            raise CommandError(f"File not found: {csv_path}")

        brand_cache = {}
        sub_brand_cache = {}
        product_cache = {}
        market_cache = {}
        count = 0

        with transaction.atomic():
            with open(csv_path, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    brand_key = row["BRAND"]
                    if brand_key not in brand_cache:
                        brand, _ = Brand.objects.get_or_create(description=row["BRAND"])
                        brand_cache[brand_key] = brand
                    brand = brand_cache[brand_key]

                    sub_brand_key = (row["SUBBRAND"], brand.id)
                    if sub_brand_key not in sub_brand_cache:
                        sub_brand, _ = SubBrand.objects.get_or_create(
                            description=row["SUBBRAND"], brand=brand
                        )
                        sub_brand_cache[sub_brand_key] = sub_brand
                    sub_brand = sub_brand_cache[sub_brand_key]

                    product_key = (row["Product"], sub_brand.id)
                    if product_key not in product_cache:
                        product, _ = Product.objects.get_or_create(
                            description=row["Product"], sub_brand=sub_brand
                        )
                        product_cache[product_key] = product
                    product = product_cache[product_key]

                    market_key = (row["M Desc"], row["M Desc 2"])
                    if market_key not in market_cache:
                        market, _ = Market.objects.get_or_create(
                            description=row["M Desc"],
                            description_2=row["M Desc 2"],
                        )
                        market_cache[market_key] = market
                    market = market_cache[market_key]

                    match = re.search(r"(\d+)WKS", row["TIME"])
                    if not match:
                        raise ValueError(
                            f"Cannot parse period_weeks from TIME: {row['TIME']!r}"
                        )

                    try:
                        value = Decimal(row["VAL"])
                    except InvalidOperation:
                        raise ValueError(f"Cannot parse value from VAL: {row['VAL']!r}")

                    wtd_raw = row["WTD"].strip()
                    if wtd_raw:
                        try:
                            weighted_distribution = Decimal(wtd_raw)
                        except InvalidOperation:
                            raise ValueError(f"Cannot parse weighted_distribution from WTD: {row['WTD']!r}")
                    else:
                        weighted_distribution = None

                    _, created = Data.objects.get_or_create(
                        market=market,
                        product=product,
                        date=datetime.date.fromisoformat(row["DATETIME"]),
                        defaults={
                            "value": value,
                            "weighted_distribution": weighted_distribution,
                            "period_weeks": int(match.group(1)),
                        },
                    )
                    if created:
                        count += 1

        self.stdout.write(f"Loaded {count} rows from {filename}.")
