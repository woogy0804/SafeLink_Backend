"""Download the official latest Tranco list and build its SQLite snapshot."""

import hashlib
import shutil
import tempfile
import zipfile
from pathlib import Path

import requests

from scripts.build_metric_snapshot import (
    DEFAULT_TRANCO_DATABASE,
    build_tranco_database,
)


TRANCO_LIST_URL = "https://tranco-list.eu/top-1m.csv.zip"
TRANCO_LIST_ID_URL = "https://tranco-list.eu/top-1m-id"
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_CSV_BYTES = 200 * 1024 * 1024
DOWNLOAD_TIMEOUT = (5, 60)


def _download_archive(destination: Path) -> str:
    digest = hashlib.sha256()
    downloaded_bytes = 0
    with requests.get(
        TRANCO_LIST_URL,
        stream=True,
        timeout=DOWNLOAD_TIMEOUT,
        headers={"User-Agent": "SafeLink-FeatureDataUpdater/1.0"},
    ) as response:
        response.raise_for_status()
        with destination.open("wb") as output_file:
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                downloaded_bytes += len(chunk)
                if downloaded_bytes > MAX_ARCHIVE_BYTES:
                    raise ValueError("Tranco 압축 파일이 허용 크기를 초과했습니다.")
                digest.update(chunk)
                output_file.write(chunk)
    return digest.hexdigest()


def _extract_csv(archive_path: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        csv_members = [item for item in archive.infolist() if item.filename.endswith(".csv")]
        if len(csv_members) != 1:
            raise ValueError("Tranco 압축 파일의 CSV 구성이 올바르지 않습니다.")
        member = csv_members[0]
        if member.file_size > MAX_CSV_BYTES:
            raise ValueError("Tranco CSV가 허용 크기를 초과했습니다.")
        with archive.open(member) as source, destination.open("wb") as output:
            shutil.copyfileobj(source, output)


def _fetch_snapshot_id() -> str:
    response = requests.get(
        TRANCO_LIST_ID_URL,
        timeout=DOWNLOAD_TIMEOUT,
        headers={"User-Agent": "SafeLink-FeatureDataUpdater/1.0"},
    )
    response.raise_for_status()
    snapshot_id = response.text.strip()
    if not snapshot_id or len(snapshot_id) > 100:
        raise ValueError("Tranco snapshot ID 응답이 올바르지 않습니다.")
    return snapshot_id


def update_tranco(output_path: Path = DEFAULT_TRANCO_DATABASE) -> int:
    with tempfile.TemporaryDirectory() as temporary_directory:
        temporary_path = Path(temporary_directory)
        archive_path = temporary_path / "top-1m.csv.zip"
        csv_path = temporary_path / "top-1m.csv"
        archive_sha256 = _download_archive(archive_path)
        _extract_csv(archive_path, csv_path)
        snapshot_id = _fetch_snapshot_id()
        return build_tranco_database(
            csv_path,
            output_path,
            source=f"{TRANCO_LIST_URL}#sha256={archive_sha256}",
            snapshot_id=snapshot_id,
            minimum_rows=100_000,
        )


def main() -> None:
    row_count = update_tranco()
    print(f"완료: Tranco {row_count:,}개 도메인 갱신")


if __name__ == "__main__":
    main()
