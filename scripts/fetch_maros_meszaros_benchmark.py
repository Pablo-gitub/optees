#!/usr/bin/env python3
"""
Acquisition and verification script for the Maros–Mészáros convex QP benchmark collection.

Downloads original archives from the primary author source (Imperial College London)
or an authoritative mirror, verifies SHA-256 checksums, and safely extracts instances
into a local cache directory outside the git repository.

Default cache directory:
    ~/.cache/optees/benchmarks/maros_meszaros/

Usage:
    python scripts/fetch_maros_meszaros_benchmark.py
    python scripts/fetch_maros_meszaros_benchmark.py --check-only
    python scripts/fetch_maros_meszaros_benchmark.py --target-dir /path/to/cache
"""

from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path
import sys
import urllib.request
import zipfile


PRIMARY_BASE_URL = "http://www.doc.ic.ac.uk/~im"

ARCHIVES_MANIFEST = {
    "00README.QP": {
        "url": f"{PRIMARY_BASE_URL}/00README.QP",
        "sha256": "cde81a616bbcb6379190ce845295be034c6676ca247e4484d5d8b7ead0daf4ce",
        "max_bytes": 100_000,
        "is_zip": False,
    },
    "QPDATA1.ZIP": {
        "url": f"{PRIMARY_BASE_URL}/QPDATA1.ZIP",
        "sha256": "1a851ba04d002c1e623367dd78a4c7d71730fc58f1296e7f83afa41e412b2323",
        "max_bytes": 15_000_000,
        "is_zip": True,
    },
    "QPDATA2.ZIP": {
        "url": f"{PRIMARY_BASE_URL}/QPDATA2.ZIP",
        "sha256": "8e96a76e3fcdac1999626926f3fa629fa7476b01a51b8d6cd312cc539e79994f",
        "max_bytes": 5_000_000,
        "is_zip": True,
    },
    "QPDATA3.ZIP": {
        "url": f"{PRIMARY_BASE_URL}/QPDATA3.ZIP",
        "sha256": "bc60bb823783ba10301ad48e4e8cca4d4af2a743ea739551ecb1c0ce40e21ed5",
        "max_bytes": 25_000_000,
        "is_zip": True,
    },
}

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "optees" / "benchmarks" / "maros_meszaros"


def _safe_extract_zip(zip_data: bytes, target_dir: Path) -> int:
    """Extract zip bytes ensuring strict protection against path traversal."""
    extracted = 0
    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        for member in zf.infolist():
            # Check for path traversal attempts
            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError(f"Insecure zip entry detected: {member.filename}")
            # Reject symlinks
            if (member.external_attr >> 16) & 0o120000 == 0o120000:
                raise ValueError(f"Symlink zip entry detected: {member.filename}")

            # Extract regular files
            if not member.is_dir():
                target_file = target_dir / member_path.name
                target_file.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, open(target_file, "wb") as dst:
                    dst.write(src.read())
                extracted += 1
    return extracted


def fetch_and_verify(
    target_dir: Path,
    *,
    check_only: bool = False,
    timeout: float = 30.0,
    verbose: bool = True,
) -> bool:
    """Fetch archives, verify SHA-256 digests, and extract to target_dir.

    Returns True if all components are verified and ready, False otherwise.
    """
    archives_dir = target_dir / "archives"
    problems_dir = target_dir / "problems"
    archives_dir.mkdir(parents=True, exist_ok=True)
    problems_dir.mkdir(parents=True, exist_ok=True)

    all_ok = True

    for filename, meta in ARCHIVES_MANIFEST.items():
        archive_path = archives_dir / filename
        expected_sha = meta["sha256"]

        # Check existing file
        if archive_path.is_file():
            computed_sha = hashlib.sha256(archive_path.read_bytes()).hexdigest()
            if computed_sha == expected_sha:
                if verbose:
                    print(f"Verified cached {filename} ({computed_sha[:12]}...)")
                continue
            else:
                if verbose:
                    print(f"Checksum mismatch for cached {filename}; re-downloading...")
                archive_path.unlink(missing_ok=True)

        if check_only:
            if verbose:
                print(f"Missing or invalid archive in check-only mode: {filename}")
            all_ok = False
            continue

        # Download
        url = meta["url"]
        if verbose:
            print(f"Downloading {filename} from {url}...")
        req = urllib.request.Request(
            url, headers={"User-Agent": "Optees-Benchmark-Acquisition/1.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = response.read(meta["max_bytes"] + 1)
                if len(data) > meta["max_bytes"]:
                    raise ValueError(
                        f"Download exceeded maximum permitted size {meta['max_bytes']} bytes"
                    )
        except Exception as exc:
            print(f"Failed to download {filename}: {exc}", file=sys.stderr)
            all_ok = False
            continue

        computed_sha = hashlib.sha256(data).hexdigest()
        if computed_sha != expected_sha:
            print(
                f"Checksum error on {filename}: expected {expected_sha}, got {computed_sha}",
                file=sys.stderr,
            )
            all_ok = False
            continue

        archive_path.write_bytes(data)
        if verbose:
            print(f"Saved {filename} ({len(data)} bytes, sha256={computed_sha[:12]}...)")

        if meta["is_zip"]:
            extracted_count = _safe_extract_zip(data, problems_dir)
            if verbose:
                print(f"Extracted {extracted_count} instances from {filename} into {problems_dir}")
        else:
            (target_dir / filename).write_bytes(data)

    return all_ok


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download and verify the Maros–Mészáros benchmark collection."
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=DEFAULT_CACHE_DIR,
        help=f"Target cache directory (default: {DEFAULT_CACHE_DIR})",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Check cache integrity without downloading missing files.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean target directory before fetching.",
    )
    args = parser.parse_args()

    if args.clean and args.target_dir.exists():
        print(f"Cleaning {args.target_dir}...")
        for p in sorted(args.target_dir.glob("**/*"), reverse=True):
            if p.is_file() or p.is_symlink():
                p.unlink()
            elif p.is_dir():
                p.rmdir()

    success = fetch_and_verify(args.target_dir, check_only=args.check_only)
    if success:
        print("All Maros–Mészáros benchmark files are verified and ready.")
        return 0
    else:
        print("Benchmark acquisition / verification failed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
