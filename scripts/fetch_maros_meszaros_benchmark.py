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
import os
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlparse
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

SELECTED_INSTANCE_MANIFEST = {
    "HS21.QPS": ("QPDATA1.ZIP", "2026bc5a854c9e12c3317c0a281268ba74c1233436a2f3540e62bd1dd6d934ec"),
    "QPTEST.QPS": (
        "QPDATA3.ZIP",
        "0959aa0e31b8dc8239690a6390fc319d23c9a8467cf348164141a0e82fa92490",
    ),
    "TAME.QPS": ("QPDATA1.ZIP", "1e688c7bcd8e73879463278b9d93d00bf5eecb0acd172aa8a97df4cbe2b5904e"),
    "ZECEVIC2.QPS": (
        "QPDATA1.ZIP",
        "1091fb5c12c4f10718d6fbab35bb8ec701648a289d14977bcb98aa88f02eab01",
    ),
    "HS35.QPS": ("QPDATA1.ZIP", "e8ef393def15d86bd4d9a2d463b6a19a4bfd43b71164e27a6e6ecbcf9979cd82"),
    "HS76.QPS": ("QPDATA1.ZIP", "392b7f31f2e174b2a7ff28f7ae40b5411e4dd1f47a75adf5c5f2b4b1b7c30df6"),
    "HS51.QPS": ("QPDATA1.ZIP", "479ba38c0dd9a3415268c350cf4b668bf28ae1f971010dbbe47aa43e38bcc040"),
    "HS52.QPS": ("QPDATA1.ZIP", "98d7f7ed93b1ad9694f9b55ae59343b79e919f53d108b7eadce3e22aa151b8b7"),
    "GENHS28.QPS": (
        "QPDATA1.ZIP",
        "acadeb848d71d7ccace41451d78e6cf710a985daaa265e84debbff010c5a1560",
    ),
    "LOTSCHD.QPS": (
        "QPDATA1.ZIP",
        "244445062ce2ea8f1d09e289bfeea4632b094d5fc83bab3b85de81718369e8eb",
    ),
    "HS118.QPS": (
        "QPDATA1.ZIP",
        "78bdddede419c9fe212edc9d5725876fb307a83eb338815f8ebe8bdc0f633040",
    ),
    "QAFIRO.QPS": (
        "QPDATA2.ZIP",
        "f914d7af0a75383dcb1b7993512b5772d09752e34d95cc22a48a356537be798a",
    ),
    "CVXQP2_S.QPS": (
        "QPDATA1.ZIP",
        "c7131355e795b3e6bdc8ac5736f9a6c18afe055f7a194deef27e92d45980432c",
    ),
    "CVXQP3_S.QPS": (
        "QPDATA1.ZIP",
        "e8676449606aaccd1b94d2b0f5e9b8cf71b8e78cfa503bc796e888101557dd01",
    ),
}

MAX_SELECTED_INSTANCE_BYTES = 5_000_000
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 175_000_000

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "optees" / "benchmarks" / "maros_meszaros"


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _safe_extract_selected(zip_data: bytes, archive_name: str, target_dir: Path) -> int:
    """Verify an archive and atomically extract only the frozen benchmark subset."""
    expected = {
        name: digest
        for name, (source_archive, digest) in SELECTED_INSTANCE_MANIFEST.items()
        if source_archive == archive_name
    }
    extracted: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        total_uncompressed = sum(member.file_size for member in zf.infolist())
        if total_uncompressed > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
            raise ValueError(f"Archive {archive_name} exceeds the uncompressed-size safety limit")
        for member in zf.infolist():
            # Check for path traversal attempts
            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError(f"Insecure zip entry detected: {member.filename}")
            # Reject symlinks
            if (member.external_attr >> 16) & 0o120000 == 0o120000:
                raise ValueError(f"Symlink zip entry detected: {member.filename}")

            basename = member_path.name.upper()
            if member.is_dir() or basename not in expected:
                continue
            if basename in extracted:
                raise ValueError(f"Duplicate selected archive entry: {basename}")
            if member.file_size > MAX_SELECTED_INSTANCE_BYTES:
                raise ValueError(f"Selected instance {basename} exceeds its size limit")
            with zf.open(member) as source:
                data = source.read(MAX_SELECTED_INSTANCE_BYTES + 1)
            if len(data) > MAX_SELECTED_INSTANCE_BYTES or len(data) != member.file_size:
                raise ValueError(f"Invalid extracted size for selected instance {basename}")
            digest = hashlib.sha256(data).hexdigest()
            if digest != expected[basename]:
                raise ValueError(
                    f"Checksum error for selected instance {basename}: "
                    f"expected {expected[basename]}, got {digest}"
                )
            extracted[basename] = data

    missing = sorted(set(expected) - set(extracted))
    if missing:
        raise ValueError(f"Archive {archive_name} lacks selected instances: {missing}")
    for basename, data in extracted.items():
        _atomic_write(target_dir / basename, data)
    return len(extracted)


def verify_selected_instances(problems_dir: Path, *, verbose: bool = True) -> bool:
    all_ok = True
    for filename, (_, expected_digest) in SELECTED_INSTANCE_MANIFEST.items():
        path = problems_dir / filename
        if not path.is_file():
            if verbose:
                print(f"Missing selected instance: {filename}")
            all_ok = False
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected_digest:
            if verbose:
                print(f"Checksum mismatch for selected instance: {filename}")
            all_ok = False
    return all_ok


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
    if not check_only:
        archives_dir.mkdir(parents=True, exist_ok=True)
        problems_dir.mkdir(parents=True, exist_ok=True)

    all_ok = True

    for filename, meta in ARCHIVES_MANIFEST.items():
        archive_path = archives_dir / filename
        expected_sha = meta["sha256"]

        # Check existing file
        data: bytes | None = None
        if archive_path.is_file():
            cached_data = archive_path.read_bytes()
            computed_sha = hashlib.sha256(cached_data).hexdigest()
            if computed_sha == expected_sha:
                data = cached_data
                if verbose:
                    print(f"Verified cached {filename} ({computed_sha[:12]}...)")
            else:
                if verbose:
                    action = "invalid in check-only mode" if check_only else "re-downloading"
                    print(f"Checksum mismatch for cached {filename}; {action}...")
                if not check_only:
                    archive_path.unlink(missing_ok=True)

        if data is None and check_only:
            if verbose:
                print(f"Missing or invalid archive in check-only mode: {filename}")
            all_ok = False
            continue

        if data is None:
            url = meta["url"]
            if verbose:
                print(f"Downloading {filename} from {url}...")
            req = urllib.request.Request(
                url, headers={"User-Agent": "Optees-Benchmark-Acquisition/1.0"}
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    final_url = urlparse(response.geturl())
                    if final_url.hostname != "www.doc.ic.ac.uk" or final_url.scheme not in {
                        "http",
                        "https",
                    }:
                        raise ValueError(f"Download redirected to an untrusted origin: {final_url}")
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

        if not check_only:
            _atomic_write(archive_path, data)
        if verbose and not check_only:
            print(f"Saved {filename} ({len(data)} bytes, sha256={computed_sha[:12]}...)")

        if meta["is_zip"] and not check_only:
            extracted_count = _safe_extract_selected(data, filename, problems_dir)
            if verbose:
                print(f"Extracted {extracted_count} instances from {filename} into {problems_dir}")
        elif not meta["is_zip"] and not check_only:
            _atomic_write(target_dir / filename, data)

    if not verify_selected_instances(problems_dir, verbose=verbose):
        all_ok = False

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
    args = parser.parse_args()

    success = fetch_and_verify(args.target_dir, check_only=args.check_only)
    if success:
        print("All Maros–Mészáros benchmark files are verified and ready.")
        return 0
    else:
        print("Benchmark acquisition / verification failed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
