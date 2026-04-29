from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


REQUIRED_SUFFIXES = {
    "data": "_data.parquet",
    "mkt": "_mkt.parquet",
    "per": "_per.parquet",
    "prod": "_prod.parquet",
}


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

        self._discover_files(folder)

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
