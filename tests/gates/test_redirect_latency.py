"""CI gate for SLI 1, redirect latency (docs/slis.md).

Starts a real uvicorn server, creates a link, follows it N times and asserts the
p95 is under the SLO documented in docs/slis.md. The threshold is parsed from
that file, so this gate cannot drift from the documented target.

Measurement note: each sample is the client-observed round trip for
GET /{code} over loopback (no redirect followed), which includes HTTP client
overhead. It is an upper bound on server time, so passing here means the server
time is under the SLO too.
"""

import math
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
SLIS_DOC = ROOT / "docs" / "slis.md"

WARMUP_REQUESTS = 10
MEASURED_REQUESTS = 200
STARTUP_TIMEOUT_SECONDS = 20


def documented_p95_slo_ms() -> float:
    """Read the redirect-latency SLO (e.g. '< 50 ms') from the SLI table in docs/slis.md."""
    for line in SLIS_DOC.read_text(encoding="utf-8").splitlines():
        if "Redirect latency" in line:
            match = re.search(r"<\s*(\d+(?:\.\d+)?)\s*ms", line)
            if match:
                return float(match.group(1))
    raise AssertionError(f"Could not find the redirect-latency SLO in {SLIS_DOC}")


def p95(samples_ms: list[float]) -> float:
    """Nearest-rank 95th percentile."""
    ordered = sorted(samples_ms)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server_url():
    port = free_port()
    url = f"http://127.0.0.1:{port}"
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "snip.main:app",
            "--app-dir", "src", "--host", "127.0.0.1", "--port", str(port),
            "--log-level", "warning",
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
        while True:
            if proc.poll() is not None:
                raise RuntimeError(f"uvicorn exited early:\n{proc.stdout.read()}")
            try:
                if httpx.get(f"{url}/api/links", timeout=1).status_code == 200:
                    break
            except httpx.TransportError:
                pass
            if time.monotonic() > deadline:
                raise RuntimeError(f"uvicorn not ready after {STARTUP_TIMEOUT_SECONDS}s")
            time.sleep(0.1)
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        proc.stdout.close()


def test_redirect_p95_is_under_documented_slo(server_url, capsys):
    slo_ms = documented_p95_slo_ms()

    with httpx.Client(base_url=server_url, timeout=5) as client:
        created = client.post("/api/links", json={"url": "https://example.com"})
        assert created.status_code == 201
        path = f"/{created.json()['code']}"

        for _ in range(WARMUP_REQUESTS):
            assert client.get(path, follow_redirects=False).status_code == 307

        samples_ms = []
        for _ in range(MEASURED_REQUESTS):
            start = time.perf_counter()
            response = client.get(path, follow_redirects=False)
            samples_ms.append((time.perf_counter() - start) * 1000)
            assert response.status_code == 307

    measured = p95(samples_ms)
    # capsys.disabled() so the numbers reach the CI log even when the test passes.
    with capsys.disabled():
        print(
            f"\nSLI 1 redirect latency: p95 = {measured:.2f} ms "
            f"(SLO < {slo_ms:g} ms, margin {slo_ms - measured:+.2f} ms; "
            f"n={len(samples_ms)}, p50 = {sorted(samples_ms)[len(samples_ms) // 2]:.2f} ms, "
            f"max = {max(samples_ms):.2f} ms)"
        )

    assert measured < slo_ms, f"p95 {measured:.2f} ms is not under the {slo_ms:g} ms SLO"
