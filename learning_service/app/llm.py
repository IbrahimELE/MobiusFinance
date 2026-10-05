"""Optional LLM layer: rewrite the rule profile + raw notes as natural instructions.

Same provider order as agent_service: ANTHROPIC_API_KEY -> logged-in `claude`
CLI -> unavailable. Any failure means the rule profile is used instead.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile

import httpx

PROMPT = """Ti pomažeš financijskom AI analitičaru da se prilagodi korisniku.
Ispod su ocjene koje je korisnik dao briefovima (teza o dionici) i preferencije koje su iz njih izvučene pravilima.

Ocjene (najstarije prvo):
{feedback}

Preferencije iz pravila: {rules}

Vrati ISKLJUČIVO JSON objekat, bez ikakvog drugog teksta:
{{"instructions": "2-3 rečenice na bosanskom, u imperativu, upućene analitičaru: kako da piše teze za ovog korisnika. Ne izmišljaj želje koje nisu u ocjenama.",
  "label": "najviše 80 znakova, sažetak naučenog za prikaz korisniku, npr. 'fokus na dug i FCF · kraće · bez opisa proizvoda'"}}"""


class LLMUnavailable(Exception):
    pass


def _call(prompt: str) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        r = httpx.post(
            "https://api.anthropic.com/v1/messages", timeout=60,
            headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
            json={"model": os.environ.get("LLM_MODEL", "claude-sonnet-4-5"), "max_tokens": 400,
                  "messages": [{"role": "user", "content": prompt}]},
        )
        r.raise_for_status()
        return r.json()["content"][0]["text"].strip()
    if shutil.which("claude"):
        r = subprocess.run(["claude", "-p", prompt, "--strict-mcp-config"], capture_output=True, text=True,
                           encoding="utf-8", timeout=120, cwd=tempfile.gettempdir())
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
        raise LLMUnavailable(r.stderr[:200] or "claude -p returned nothing")
    raise LLMUnavailable("no ANTHROPIC_API_KEY and no claude CLI")


def summarise(feedback: list[dict], rules: dict) -> dict:
    """Return {"instructions", "label"}; raises LLMUnavailable on any problem."""
    lines = [
        f"- {f['ticker']}: {'👍' if f['rating'] == 'up' else '👎'} {f.get('note') or ''} {('tagovi: ' + ', '.join(f['tags'])) if f.get('tags') else ''}".rstrip()
        for f in feedback[-12:]
    ]
    try:
        raw = _call(PROMPT.format(feedback="\n".join(lines), rules=json.dumps(rules, ensure_ascii=False)))
        match = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(match.group(0) if match else raw)
        instructions, label = str(data["instructions"]).strip(), str(data["label"]).strip()[:120]
    except LLMUnavailable:
        raise
    except Exception as e:  # network, JSON, missing keys: all mean "use rules"
        raise LLMUnavailable(f"bad LLM answer: {e}") from e
    if not instructions:
        raise LLMUnavailable("empty instructions")
    return {"instructions": instructions, "label": label}
