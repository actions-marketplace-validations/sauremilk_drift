#!/usr/bin/env python3
"""Cross-Version Benchmark — run stable corpus against multiple drift releases.

Installs each requested drift-analyzer version in an isolated venv, runs
``drift analyze`` against a reproducible corpus, and records per-signal
recall plus overall metrics.

Usage:
    python scripts/benchmark_cross_version.py
    python scripts/benchmark_cross_version.py --versions 1.3.0 2.1.0
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Corpus manifest (expected detections per signal)
# ---------------------------------------------------------------------------
CORPUS_DIR = Path(__file__).resolve().parent.parent / "benchmarks" / "corpus"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"

# Versions worth benchmarking (must be on PyPI as drift-analyzer).
DEFAULT_VERSIONS: list[str] = [
    # "1.0.0",  # uncomment once available on PyPI
    "1.3.0",
    "2.0.0",
    "2.1.0",
]


@dataclass
class SignalResult:
    """Detection result for one signal in one version."""

    expected: int = 0
    detected: int = 0

    @property
    def recall(self) -> float:
        """Recall for this signal."""
        return self.detected / self.expected if self.expected else 0.0


@dataclass
class VersionResult:
    """Aggregated result for one drift version."""

    version: str = ""
    signals_available: int = 0
    total_findings: int = 0
    total_expected: int = 0
    total_detected: int = 0
    overall_recall: float = 0.0
    per_signal: dict[str, dict[str, float | int]] = field(
        default_factory=dict,
    )
    error: str | None = None


def _create_venv(version: str, tmp: Path) -> Path:
    """Create an isolated venv with a specific drift-analyzer version."""
    venv_dir = tmp / f"venv_{version}"
    subprocess.run(
        [sys.executable, "-m", "venv", str(venv_dir)],
        check=True,
        capture_output=True,
    )
    pip = (
        venv_dir / "Scripts" / "pip.exe"
        if sys.platform == "win32"
        else venv_dir / "bin" / "pip"
    )
    subprocess.run(
        [str(pip), "install", f"drift-analyzer=={version}"],
        check=True,
        capture_output=True,
        timeout=120,
    )
    return venv_dir


def _drift_exe(venv_dir: Path) -> Path:
    """Return path to drift executable inside venv."""
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "drift.exe"
    return venv_dir / "bin" / "drift"


def _prepare_corpus(tmp: Path) -> Path:
    """Copy the benchmark corpus into a temp directory and init git."""
    corpus_copy = tmp / "corpus"
    shutil.copytree(CORPUS_DIR, corpus_copy)

    # Initialize git repo for TVS signal.
    init_script = corpus_copy / "init_git.sh"
    if init_script.exists():
        if sys.platform == "win32":
            # Use git bash on Windows.
            subprocess.run(
                ["git", "init"],
                cwd=str(corpus_copy),
                capture_output=True,
            )
            subprocess.run(
                ["git", "add", "."],
                cwd=str(corpus_copy),
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "init", "--allow-empty"],
                cwd=str(corpus_copy),
                capture_output=True,
                env={
                    **os.environ,
                    "GIT_AUTHOR_NAME": "bench",
                    "GIT_COMMITTER_NAME": "bench",
                    "GIT_AUTHOR_EMAIL": "b@b",
                    "GIT_COMMITTER_EMAIL": "b@b",
                },
            )
        else:
            subprocess.run(
                ["bash", str(init_script)],
                cwd=str(corpus_copy),
                capture_output=True,
            )
    else:
        # Minimal git init for drift to work.
        subprocess.run(
            ["git", "init"],
            cwd=str(corpus_copy),
            capture_output=True,
        )
        subprocess.run(
            ["git", "add", "."],
            cwd=str(corpus_copy),
            capture_output=True,
        )
        env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "bench",
            "GIT_COMMITTER_NAME": "bench",
            "GIT_AUTHOR_EMAIL": "b@b",
            "GIT_COMMITTER_EMAIL": "b@b",
        }
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=str(corpus_copy),
            capture_output=True,
            env=env,
        )

    return corpus_copy


def _run_drift(
    drift_exe: Path,
    corpus_path: Path,
) -> dict | None:
    """Run drift analyze and return parsed JSON output."""
    result = subprocess.run(
        [
            str(drift_exe),
            "analyze",
            "--repo",
            str(corpus_path),
            "--format",
            "json",
            "--exit-zero",
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0 and not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def _load_manifest() -> dict:
    """Load the corpus manifest (expected detections)."""
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _match_findings(
    drift_output: dict,
    manifest: dict,
) -> VersionResult:
    """Match drift findings against manifest expectations."""
    vr = VersionResult()

    expectations = manifest.get("expectations", {})
    findings = drift_output.get("findings", [])

    signals_seen: set[str] = set()
    for f in findings:
        st = f.get("signal_type", "")
        signals_seen.add(st)

    vr.total_findings = len(findings)
    vr.signals_available = len(
        {f.get("signal_type") for f in findings if f.get("signal_type")},
    )

    for signal_name, expected_count in expectations.items():
        # Count findings matching this signal.
        matched = sum(
            1
            for f in findings
            if f.get("signal_type", "") == signal_name
        )
        detected = min(matched, expected_count)
        vr.total_expected += expected_count
        vr.total_detected += detected
        vr.per_signal[signal_name] = {
            "expected": expected_count,
            "detected": detected,
            "recall": detected / expected_count if expected_count else 0.0,
            "finding_count": matched,
        }

    vr.overall_recall = (
        vr.total_detected / vr.total_expected
        if vr.total_expected
        else 0.0
    )
    return vr


def benchmark_version(
    version: str,
    corpus_path: Path,
    manifest: dict,
    tmp: Path,
) -> VersionResult:
    """Benchmark a single drift version against the corpus."""
    vr = VersionResult(version=version)
    try:
        venv_dir = _create_venv(version, tmp)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        vr.error = f"Install failed: {exc}"
        return vr

    drift_exe = _drift_exe(venv_dir)
    if not drift_exe.exists():
        vr.error = f"drift executable not found at {drift_exe}"
        return vr

    output = _run_drift(drift_exe, corpus_path)
    if output is None:
        vr.error = "drift analyze returned no valid JSON"
        return vr

    vr = _match_findings(output, manifest)
    vr.version = version
    return vr


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Cross-version benchmark runner",
    )
    parser.add_argument(
        "--versions",
        nargs="+",
        default=DEFAULT_VERSIONS,
        help="Versions to benchmark (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        default="benchmark_results/cross_version_benchmark.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    if not MANIFEST_PATH.exists():
        print(
            f"ERROR: Corpus manifest not found at {MANIFEST_PATH}",
            file=sys.stderr,
        )
        print(
            "Run: python scripts/signal_coverage_matrix.py first, "
            "then ensure benchmarks/corpus/ exists.",
            file=sys.stderr,
        )
        sys.exit(1)

    manifest = _load_manifest()
    results: list[dict] = []

    with tempfile.TemporaryDirectory(prefix="drift_bench_") as tmp_str:
        tmp = Path(tmp_str)
        corpus_path = _prepare_corpus(tmp)

        for version in args.versions:
            print(f"Benchmarking drift-analyzer=={version} ...")
            vr = benchmark_version(version, corpus_path, manifest, tmp)
            result_dict = {
                "version": vr.version,
                "signals_available": vr.signals_available,
                "total_findings": vr.total_findings,
                "total_expected": vr.total_expected,
                "total_detected": vr.total_detected,
                "overall_recall": round(vr.overall_recall, 4),
                "per_signal": vr.per_signal,
            }
            if vr.error:
                result_dict["error"] = vr.error
            results.append(result_dict)

            if vr.error:
                print(f"  ERROR: {vr.error}")
            else:
                print(
                    f"  Recall: {vr.overall_recall:.1%}"
                    f"  ({vr.total_detected}/{vr.total_expected})"
                    f"  Findings: {vr.total_findings}"
                )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    output_data = {
        "benchmark": "cross_version",
        "versions": {r["version"]: r for r in results},
    }
    out_path.write_text(
        json.dumps(output_data, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
