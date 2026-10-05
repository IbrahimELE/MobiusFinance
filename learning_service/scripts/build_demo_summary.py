"""Ask the LLM once for the demo feedback's summary and commit it as demo/llm_summary.json,
so the demo shows the AI-written profile even offline.

    python -m scripts.build_demo_summary      (from learning_service/)
"""

import json

from app.llm import summarise
from app.rules import build_profile
from app.service import DEMO_DIR, feedback_key

items = json.loads((DEMO_DIR / "feedback.json").read_text(encoding="utf-8"))
rules = build_profile(items)
summary = summarise(items, {"focus": rules.focus, "avoid": rules.avoid, "style": rules.style})
out = {"key": feedback_key(items), **summary}
(DEMO_DIR / "llm_summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=1))
