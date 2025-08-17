"""SKU verification via RAG judge pipeline.

This module exposes :func:`judge_same_product` which compares two
product descriptions using web snippets and an LLM.  It follows the flow
outlined in conversation: parse attributes, retrieve web snippets, and
have an LLM judge whether the products match.

The ``web_search_snippets`` function is currently a stub; wire it up to a
real search provider (Bing, Google, SerpAPI, etc.) for production use.
"""
from __future__ import annotations

import json
import os
import re
import textwrap
from typing import Dict, List

from openai import OpenAI

# Initialize the OpenAI client using the environment variable
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def canon(s: str) -> str:
    """Return a normalized version of ``s`` for easier parsing."""
    s = s.upper().replace("×", "X").replace('"', "IN")
    s = re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 /X\.-]", " ", s)).strip()
    s = s.replace("SCHEDULE 40", "SCH 40").replace("SCHEDULE 80", "SCH 80")
    return s


def parse_attrs(desc: str) -> Dict:
    """Parse key attributes from a product ``desc`` string."""
    s = canon(desc)
    attrs = {
        "material": next(
            (
                m
                for m in ["CPVC", "PVC", "BRASS", "COPPER", "GALV", "SS"]
                if m in s.split()
            ),
            None,
        ),
        "type": next(
            (
                t
                for t in [
                    "ELBOW",
                    "ELL",
                    "TEE",
                    "WYE",
                    "COUPLING",
                    "REDUCER",
                    "BUSHING",
                    "CAP",
                    "UNION",
                    "ADAPTER",
                    "NIPPLE",
                ]
                if t in s.split()
            ),
            None,
        ),
        "schedule": "SCH80"
        if "SCH 80" in s or "SCH80" in s
        else ("SCH40" if "SCH 40" in s or "SCH40" in s else None),
        "angle_deg": 90
        if any(t in s for t in [" 90 ", " 90D", " 90DEG", "1/4 BEND", "1/4BEND"])
        else (
            45
            if any(
                t in s
                for t in [" 45 ", " 45D", " 45DEG", "1/8 BEND", "1/8BEND"]
            )
            else (
                22.5
                if any(
                    t in s
                    for t in [
                        "22.5",
                        "22-1/2",
                        "1/16 BEND",
                        "1/16BEND",
                    ]
                )
                else (
                    11.25
                    if any(
                        t in s
                        for t in [
                            "11.25",
                            "11-1/4",
                            "1/32 BEND",
                            "1/32BEND",
                        ]
                    )
                    else None
                )
            )
        ),
        "ends": [
            e
            for e in [
                "SXS",
                "CXC",
                "SXFIP",
                "SXMIP",
                "FIP",
                "MIP",
                "FNPT",
                "MNPT",
                "SLIP",
                "SOCKET",
                "SPIGOT",
                "CTS",
            ]
            if e in s
        ],
        "sizes": re.findall(r"\b\d+(?:/\d+)?(?:X\d+(?:/\d+)?)?\b", s),
        "raw": desc,
        "canon": s,
    }
    if attrs["type"] == "ELL":
        attrs["type"] = "ELBOW"
    return attrs


def web_search_snippets(query: str, k: int = 6) -> List[Dict]:
    """Return search snippets for ``query``.

    This is currently a stub that returns an empty list. Replace the
    body with a real web search implementation using Bing Web Search,
    Google Custom Search, SerpAPI, etc. Prefer manufacturer/spec/UPC
    domains when possible.
    """
    return []


JUDGE_SYSTEM = """You are a strict plumbing SKU matching assistant.
Compare two fittings and decide if they are the SAME product.
Use only the evidence provided (descriptions + web snippets).
Hard constraints: Material, Type, Angle, Sizes, Schedule, Ends must agree.
If uncertain or conflicts exist, answer false.
Output valid JSON only with keys:
{"same_product": bool, "confidence": 0..1, "blocking_reasons": [str], "key_attributes": { ... }, "best_supporting_urls": [str]}"""


def judge_same_product(desc_a: str, desc_b: str) -> Dict:
    """Judge whether two descriptions refer to the same product."""
    a = parse_attrs(desc_a)
    b = parse_attrs(desc_b)

    q_base_a = f"{a['material']} {a['type']} {a['schedule']} {' '.join(a['sizes'])} {' '.join(a['ends'])} {a['canon']}"
    q_base_b = f"{b['material']} {b['type']} {b['schedule']} {' '.join(b['sizes'])} {' '.join(b['ends'])} {b['canon']}"

    snippets = web_search_snippets(q_base_a, k=4) + web_search_snippets(q_base_b, k=4)

    user_prompt = textwrap.dedent(
        f"""
        A description: {a['raw']}
        A parsed: {json.dumps({k: v for k, v in a.items() if k != 'raw'}, ensure_ascii=False)}

        B description: {b['raw']}
        B parsed: {json.dumps({k: v for k, v in b.items() if k != 'raw'}, ensure_ascii=False)}

        Web snippets (title | url | snippet):
        {json.dumps(snippets[:8], ensure_ascii=False, indent=2)}

        Decide if A and B are the SAME product. Follow hard constraints.
        Output JSON only.
        """
    )

    resp = client.chat.completions.create(
        model="gpt-5",
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
    )
    txt = resp.choices[0].message.content.strip()
    try:
        data = json.loads(txt)
    except Exception:
        data = {
            "same_product": False,
            "confidence": 0.0,
            "blocking_reasons": ["Invalid JSON from model"],
            "key_attributes": {},
            "best_supporting_urls": [],
        }
    return data


__all__ = ["judge_same_product", "parse_attrs", "canon"]
