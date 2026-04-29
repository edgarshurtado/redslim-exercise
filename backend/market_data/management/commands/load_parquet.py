from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


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
