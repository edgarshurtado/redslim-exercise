from decimal import Decimal
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from market_data.models import Brand, Data, Market, Product, SubBrand


REQUIRED_SUFFIXES = {
    "data": "_data.parquet",
    "mkt": "_mkt.parquet",
    "per": "_per.parquet",
    "prod": "_prod.parquet",
}

LEAF_LEVEL = "MANUFACTURER!SEGMENT!SUB SEGMENT!BRAND!SUB BRAND!PROMO/NON PROMO!SIZE!ITEM"
DATA_BATCH_SIZE = 50_000
BULK_CREATE_BATCH_SIZE = 10_000
VAL_SCALE = 1_000_000
PERIOD_WEEKS = 4
TWO_DP = Decimal("0.01")


class Command(BaseCommand):
    help = "Load retail sales data from parquet files in docs/data/<foldername>/"

    def add_arguments(self, parser):
        parser.add_argument(
            "foldername",
            type=str,
            help="Folder name in docs/data/",
        )

    def handle(self, *args, **options):
        foldername = options["foldername"]
        folder = (
            Path(__file__).resolve().parents[4] / "docs" / "data" / foldername
        )
        if not folder.is_dir():
            raise CommandError(f"Folder not found: {folder}")

        paths = self._discover_files(folder)

        with transaction.atomic():
            mkt_df = pd.read_parquet(paths["mkt"])
            per_df = pd.read_parquet(paths["per"])
            prod_df = pd.read_parquet(paths["prod"])

            prod_df = prod_df[prod_df["LEVEL"] == LEAF_LEVEL]
            if prod_df.empty:
                raise CommandError(
                    f"No leaf-level products in {paths['prod'].name}"
                )

            brand_id_by_desc = self._load_brands(prod_df)
            subbrand_id_by_pair = self._load_subbrands(prod_df, brand_id_by_desc)
            product_id_by_tag = self._load_products(
                prod_df, brand_id_by_desc, subbrand_id_by_pair
            )
            market_id_by_tag = self._load_markets(mkt_df)
            date_by_tag = dict(zip(per_df["TAG"], per_df["DATETIME"]))

            count_before = Data.objects.count()
            self._load_data(
                paths["data"],
                market_id_by_tag,
                product_id_by_tag,
                date_by_tag,
            )
            loaded = Data.objects.count() - count_before

        self.stdout.write(f"Loaded {loaded} rows from {foldername}.")

    def _discover_files(self, folder):
        paths = {}
        for key, suffix in REQUIRED_SUFFIXES.items():
            matches = sorted(folder.glob(f"*{suffix}"))
            if not matches:
                raise CommandError(
                    f"Missing required file matching *{suffix} in {folder}"
                )
            if len(matches) > 1:
                raise CommandError(
                    f"Multiple files match *{suffix} in {folder}: {matches}"
                )
            paths[key] = matches[0]
        return paths

    def _load_brands(self, prod_df):
        descs = set(prod_df["GL Brand"].dropna())
        Brand.objects.bulk_create(
            [Brand(description=d) for d in descs],
            ignore_conflicts=True,
        )
        return {
            b.description: b.pk
            for b in Brand.objects.filter(description__in=descs)
        }

    def _load_subbrands(self, prod_df, brand_id_by_desc):
        pairs = set(zip(prod_df["GL Sub Brand"], prod_df["GL Brand"]))
        SubBrand.objects.bulk_create(
            [
                SubBrand(description=sub, brand_id=brand_id_by_desc[brand])
                for sub, brand in pairs
            ],
            ignore_conflicts=True,
        )
        brand_ids = list(brand_id_by_desc.values())
        return {
            (sb.description, sb.brand_id): sb.pk
            for sb in SubBrand.objects.filter(brand_id__in=brand_ids)
        }

    def _load_products(self, prod_df, brand_id_by_desc, subbrand_id_by_pair):
        instances = [
            Product(
                description=sdesc,
                sub_brand_id=subbrand_id_by_pair[
                    (sub, brand_id_by_desc[brand])
                ],
            )
            for sdesc, sub, brand in zip(
                prod_df["SDESC"],
                prod_df["GL Sub Brand"],
                prod_df["GL Brand"],
            )
        ]
        Product.objects.bulk_create(instances, ignore_conflicts=True)

        sub_brand_ids = list(subbrand_id_by_pair.values())
        natural = {
            (p.description, p.sub_brand_id): p.pk
            for p in Product.objects.filter(sub_brand_id__in=sub_brand_ids)
        }
        return {
            tag: natural[
                (
                    sdesc,
                    subbrand_id_by_pair[(sub, brand_id_by_desc[brand])],
                )
            ]
            for tag, sdesc, sub, brand in zip(
                prod_df["TAG"],
                prod_df["SDESC"],
                prod_df["GL Sub Brand"],
                prod_df["GL Brand"],
            )
        }

    def _load_markets(self, mkt_df):
        instances = [
            Market(description=short, description_2=long_)
            for short, long_ in zip(mkt_df["SHORT"], mkt_df["LONG"])
        ]
        Market.objects.bulk_create(instances, ignore_conflicts=True)
        descs = set(mkt_df["SHORT"])
        natural = {
            (m.description, m.description_2): m.pk
            for m in Market.objects.filter(description__in=descs)
        }
        return {
            tag: natural[(short, long_)]
            for tag, short, long_ in zip(
                mkt_df["TAG"], mkt_df["SHORT"], mkt_df["LONG"]
            )
        }

    def _load_data(
        self,
        data_path,
        market_id_by_tag,
        product_id_by_tag,
        date_by_tag,
    ):
        pf = pq.ParquetFile(str(data_path))
        for batch in pf.iter_batches(batch_size=DATA_BATCH_SIZE):
            df = batch.to_pandas()
            df = df.dropna(subset=["VAL"])
            df = df[df["MARKET_TAG"].isin(market_id_by_tag)]
            df = df[df["PRODUCT_TAG"].isin(product_id_by_tag)]
            df = df[df["PERIOD_TAG"].isin(date_by_tag)]
            rows = [
                Data(
                    market_id=market_id_by_tag[mkt_tag],
                    product_id=product_id_by_tag[prod_tag],
                    date=date_by_tag[per_tag],
                    value=(Decimal(str(val)) * VAL_SCALE).quantize(TWO_DP),
                    weighted_distribution=(
                        None if pd.isna(wtd)
                        else Decimal(str(wtd)).quantize(TWO_DP)
                    ),
                    period_weeks=PERIOD_WEEKS,
                )
                for mkt_tag, prod_tag, per_tag, val, wtd in zip(
                    df["MARKET_TAG"],
                    df["PRODUCT_TAG"],
                    df["PERIOD_TAG"],
                    df["VAL"],
                    df["WTD"],
                )
            ]
            Data.objects.bulk_create(
                rows,
                ignore_conflicts=True,
                batch_size=BULK_CREATE_BATCH_SIZE,
            )
