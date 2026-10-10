"""E2E stack for UI tests: offline data_service (DATA_OFFLINE=1, temp paper account) + agent_service/UI.
No LLM (claude/API key hidden), so briefs come from agent_service/demo_cache and tests are fast and deterministic.
Run: python -m pytest frontend/tests   (needs: pip install playwright && python -m playwright install chromium)"""
import os, socket, subprocess, sys, time, uuid
from pathlib import Path
import httpx, pytest

ROOT = Path(__file__).resolve().parents[2]

def _port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); return s.getsockname()[1]

def _wait(url, proc, timeout=40):
    end = time.time() + timeout
    while time.time() < end:
        if proc.poll() is not None:
            raise RuntimeError(f"{url} exited with {proc.returncode}")
        try:
            httpx.get(url, timeout=1); return
        except httpx.HTTPError:
            time.sleep(0.3)
    raise RuntimeError(f"{url} did not start")

@pytest.fixture(scope="session")
def stack(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("stack")
    dport, aport = _port(), _port()
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "DATA_URL", "LEARNING_URL")}
    env["PATH"] = os.pathsep.join(d for d in env.get("PATH", "").split(os.pathsep)   # hide `claude` CLI -> no LLM call
                                  if d and not (Path(d) / "claude").exists() and not (Path(d) / "claude.exe").exists())
    denv = {**env, "DATA_OFFLINE": "1", "DATA_PAPER_DIR": str(tmp / "paper")}
    procs = [subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(dport)], cwd=ROOT / "data_service",
                              env=denv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)]
    try:
        _wait(f"http://127.0.0.1:{dport}/docs", procs[0])
        procs.append(subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--port", str(aport)], cwd=ROOT / "agent_service",
                                      env={**env, "DATA_URL": f"http://127.0.0.1:{dport}"}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        _wait(f"http://127.0.0.1:{aport}/features", procs[1])
        yield f"http://127.0.0.1:{aport}"
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            p.wait(10)

@pytest.fixture
def page(stack):
    pw = pytest.importorskip("playwright.sync_api")
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 900})
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.add_init_script(f"localStorage.proj='e2e-{uuid.uuid4().hex[:8]}'")   # fresh workspace = fresh paper account
        pg.goto(stack + "/")
        yield pg
        b.close()
        assert not errors, f"JS errors: {errors}"
