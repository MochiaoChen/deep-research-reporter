# src/drr/pipeline.py

import json
import math
from typing import Dict, List, Tuple, Optional

from .llm import LLM
from . import prompts, retrieval


# ---------- helpers ----------

def _round_words(n: int) -> int:
    return max(150, int(n))


def parse_intent(topic: str, word_limit: int) -> Dict:
    """Minimal intent parser; can be extended with regex/task classification."""
    return {
        "topic": topic.strip(),
        "word_limit": _round_words(word_limit),
        "audience": "general policy/industry literate audience",
    }


# ---------- outline ----------

def plan_outline(llm: LLM, intent: Dict) -> Dict:
    target = intent["word_limit"]
    messages = [
        {"role": "system", "content": prompts.SYSTEM_PROMPT},
        {"role": "user", "content": prompts.OUTLINE_PLANNER_PROMPT},
        {"role": "user", "content": f"Topic: {intent['topic']}\nTarget words: {target}"},
    ]
    raw = llm.chat(messages, max_tokens=1600)
    try:
        plan = json.loads(raw)
        # basic sanity
        if not isinstance(plan, dict) or "sections" not in plan:
            raise ValueError
    except Exception:
        # Fallback: simple 6-section skeleton
        per = max(120, math.floor(target / 6))
        plan = {
            "sections": [
                {"title": "Title & Abstract", "goal": "state title and abstract", "key_points": [], "target_words": int(per * 1.2)},
                {"title": "Key Takeaways", "goal": "3–5 bullets", "key_points": [], "target_words": int(per * 0.8)},
                {"title": "Background & Definitions", "goal": "scope and definitions", "key_points": [], "target_words": per},
                {"title": "Current Landscape", "goal": "status quo and actors", "key_points": [], "target_words": per},
                {"title": "Drivers & Implications", "goal": "mechanisms and impacts", "key_points": [], "target_words": per},
                {"title": "Conclusion", "goal": "wrap up", "key_points": [], "target_words": int(per * 0.8)},
            ],
            "total_words": target,
        }
    return plan


# ---------- section write/critique/revise ----------

def write_section(llm: LLM, section: Dict) -> str:
    # Open-book retrieval to fetch background context
    context = ""
    try:
        hits = retrieval.open_book_search(section.get("title", ""), n_results=2)
        context = "\n".join(
            f"{h['title']}: {h['summary']}" for h in hits if h.get("summary")
        )
    except Exception:
        context = ""

    spec = json.dumps(
        {
            "section_title": section.get("title", ""),
            "section_goal": section.get("goal", ""),
            "key_points": section.get("key_points", []),
            "target_words": section.get("target_words", 180),
            "context": context,
        },
        ensure_ascii=False,
    )
    messages = [
        {"role": "system", "content": prompts.SYSTEM_PROMPT},
        {"role": "user", "content": prompts.SECTION_WRITER_PROMPT},
        {"role": "user", "content": spec},
    ]
    return llm.chat(messages, max_tokens=1800)


def critic_pass(llm: LLM, section_text: str) -> Dict:
    messages = [
        {"role": "system", "content": prompts.SYSTEM_PROMPT},
        {"role": "user", "content": prompts.CRITIC_PROMPT},
        {"role": "user", "content": section_text},
    ]
    raw = llm.chat(messages, max_tokens=900, temperature=0.0)
    try:
        data = json.loads(raw)
        if not isinstance(data, dict) or "edits" not in data:
            raise ValueError("bad critic json")
        return data
    except Exception:
        return {"scores": {}, "edits": []}


def apply_revision(llm: LLM, section_text: str, edits: List[str]) -> str:
    if not edits:
        return section_text
    payload = "Edits:\n- " + "\n- ".join(edits) + "\n\nOriginal:\n" + section_text
    messages = [
        {"role": "system", "content": prompts.SYSTEM_PROMPT},
        {"role": "user", "content": prompts.REVISION_PROMPT},
        {"role": "user", "content": payload},
    ]
    return llm.chat(messages, max_tokens=1800)


# ---------- compose & wordcount ----------

def compose_report(llm: LLM, sections: List[Tuple[str, str]], target_words: int) -> str:
    bundle = "\n\n".join([f"## {t}\n\n{s}" for t, s in sections])
    messages = [
        {"role": "system", "content": prompts.SYSTEM_PROMPT},
        {"role": "user", "content": prompts.COMPOSER_PROMPT},
        {"role": "user", "content": f"TARGET_WORDS={target_words}\n\n{bundle}"},
    ]
    return llm.chat(messages, max_tokens=3500)


def polish_report(llm: LLM, report: str) -> str:
    """Refine the full report for smoother transitions and clarity."""
    messages = [
        {"role": "system", "content": prompts.SYSTEM_PROMPT},
        {"role": "user", "content": prompts.POLISH_PROMPT},
        {"role": "user", "content": report},
    ]
    return llm.chat(messages, max_tokens=3500)


def enforce_wordcount(llm: LLM, report: str, target_words: int) -> str:
    messages = [
        {"role": "system", "content": prompts.SYSTEM_PROMPT},
        {"role": "user", "content": prompts.COMPRESSOR_PROMPT.format(target=target_words)},
        {"role": "user", "content": report},
    ]
    return llm.chat(messages, max_tokens=3500, temperature=0.0)


# ---------- public APIs ----------

def _make_llm(provider: str, model: str, temperature: float = 0.35, max_tokens: int = 2200) -> LLM:
    """
    Factory to create LLM with unified defaults.
    Providers supported by llm.LLM: openai | gemini | deepseek | chatglm | anthropic
    """
    return LLM(provider=provider, model=model, temperature=temperature, max_tokens=max_tokens)


def generate_report_v2(
    topic: str,
    word_limit: int,
    provider: str = "openai",
    model: str = "gpt-4o-mini",
    temperature: float = 0.35,
) -> str:
    """
    New entry that supports multi-provider LLMs.
    """
    llm = _make_llm(provider=provider, model=model, temperature=temperature, max_tokens=2400)

    intent = parse_intent(topic, word_limit)
    plan = plan_outline(llm, intent)

    sections_out: List[Tuple[str, str]] = []
    for sec in plan["sections"]:
        text = write_section(llm, sec)
        crit = critic_pass(llm, text)
        text2 = apply_revision(llm, text, crit.get("edits", []))
        sections_out.append((sec.get("title", "Section"), text2))

    composed = compose_report(llm, sections_out, intent["word_limit"])
    polished = polish_report(llm, composed)
    final = enforce_wordcount(llm, polished, intent["word_limit"])
    return final


# Backward-compatible API (OpenAI-only by default, kept for older callers)
def generate_report(topic: str, word_limit: int, model: str = "gpt-4o-mini") -> str:
    return generate_report_v2(
        topic=topic,
        word_limit=word_limit,
        provider="openai",
        model=model,
        temperature=0.35,
    )
