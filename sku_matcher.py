"""
SKU verification via RAG judge pipeline.

This module exposes :func:`judge_same_product` which compares two
product descriptions using parsed attributes, optional web snippets,
and an LLM. It follows this flow:

1) Normalize & parse attributes from each description
2) Fast "hard attribute" judge: short-circuit obvious matches/mismatches
3) (Optional) Retrieve web snippets from a search provider
4) Ask the LLM to judge STRICTLY based on provided evidence

Providers:
- Bing Web Search API (set BING_SEARCH_KEY)
- SerpAPI for Google (set SERPAPI_KEY)
- Google Programmable Search Engine (set GOOGLE_API_KEY and GOOGLE_CSE_ID)
- DuckDuckGo Instant Answer (fallback, no key needed)

Environment:
- OPENAI_API_KEY (required for LLM)
- SKU_JUDGE_MODEL (optional; default "gpt-5")
- HTTP(S) proxies are honored via standard env variables if present.

Usage:
    from sku_judge import judge_same_product
    result = judge_same_product("CPVC SCH80 1/8 ELBOW 1-1/2\" SXS",
                                "CPVC SCH 80 45 DEG ELBOW 1-1/2\" SOCKET X SOCKET")
"""

from __future__ import annotations

import json
import os
import re
import textwrap
from collections import Counter
from functools import lru_cache
from typing import Dict, List, Optional

import requests
from openai import OpenAI


# ----------------------------
# OpenAI client & model config
# ----------------------------
MODEL = os.getenv("SKU_JUDGE_MODEL", "gpt-5")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ----------------------------
# Normalization & Parsing
# ----------------------------

def canon(s: str) -> str:
    """Return a normalized version of ``s`` for easier parsing."""
    s = (s or "")
    s = s.upper().replace("×", "X")
    s = s.replace('"', "IN")
    # unify schedule words
    s = s.replace("SCHEDULE 40", "SCH 40").replace("SCHEDULE-40", "SCH 40")
    s = s.replace("SCHEDULE 80", "SCH 80").replace("SCHEDULE-80", "SCH 80")
    s = s.replace("DWV", "DWV")  # leave DWV as-is (distinct from SCH)
    # strip non-alnum separators but preserve X, /, ., -, spaces
    s = re.sub(r"[^A-Z0-9 /X\.\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


ANGLE_SYNONYMS = {
    # bend names to degrees
    "1/4 BEND": 90, "1/4BEND": 90, "QUARTER BEND": 90,
    "1/8 BEND": 45, "1/8BEND": 45, "EIGHTH BEND": 45,
    "1/16 BEND": 22.5, "1/16BEND": 22.5,
    "1/32 BEND": 11.25, "1/32BEND": 11.25,
    "1/4 ELBOW": 90, "1/8 ELBOW": 45,
}

END_MAP = {
    # normalize to compact canonical set
    "SLIP": "S",
    "SOCKET": "S",
    "SOC": "S",
    "SXS": "S",      # treat SXS as socket ends present
    "CXC": "S",      # copper term often used synonymously for socket/socket in SKUs
    "SPIGOT": "SPG",
    "SPG": "SPG",
    "FIP": "FIP", "FNPT": "FIP",
    "MIP": "MIP", "MNPT": "MIP",
    "CTS": "CTS",
}


def _norm_fraction_size_token(tok: str) -> str:
    """Canonicalize a single size token (e.g., 1-1/2, 1 1/2IN, 1.5, 3IN → 3)."""
    t = (tok or "").upper()
    t = t.replace('"', '').replace("IN", '').strip()
    t = t.replace('–', '-').replace('—', '-')
    t = re.sub(r"\s+", "", t)

    # Normalize "1 1/2" -> "1-1/2"
    t = re.sub(r"^(\d+)(?:\s+|\-)?(\d+/\d+)$", r"\1-\2", t)

    # If decimal like 1.5, map common fractional decimals
    if re.fullmatch(r"\d+\.\d+", t):
        try:
            val = float(t)
            whole = int(val)
            frac = round(val - whole, 3)
            mapping = {0.125: "1/8", 0.25: "1/4", 0.375: "3/8", 0.5: "1/2", 0.625: "5/8",
                       0.75: "3/4", 0.875: "7/8", 0.0: ""}
            if frac in mapping:
                return f"{whole}-{mapping[frac]}" if whole and mapping[frac] else (str(whole) if whole else mapping[frac])
        except Exception:
            pass
    return t


def _extract_size_sequences(S: str) -> List[List[str]]:
    """
    Find sequences of 1..4 sizes separated by X (e.g., "3", "3 X 2", "3X2X1/2").
    Returns list of token lists; each token is raw before normalization.
    """
    # Match a "size" token: 1, 1/2, 1-1/2, 1.5, optionally with IN
    size_token = r"\d+(?:-\d+/\d+|\.\d+|/\d+)?(?: ?IN)?"
    pattern = rf"\b{size_token}(?: ?X ?{size_token}){{0,3}}\b"
    hits = re.findall(pattern, S)
    seqs: List[List[str]] = []
    for h in hits:
        parts = re.split(r"\s*X\s*", h)
        seqs.append([p.strip() for p in parts if p.strip()])
    return seqs


def _norm_size_combo(desc: str) -> List[str]:
    """
    Extract and canonicalize size combos from a description.
    Picks the longest sequence if multiple are present.
    """
    S = canon(desc)
    seqs = _extract_size_sequences(S)
    if not seqs:
        return []
    best = max(seqs, key=lambda xs: sum(len(x) for x in xs))
    return [_norm_fraction_size_token(p) for p in best]


def _norm_ends(tokens: List[str], raw: str) -> List[str]:
    """
    Map varied end names to a compact canonical set and infer obvious combos.
    Returns a stable-ordered list (subset of ["SPG","S","MIP","FIP","CTS"]).
    """
    S = canon(raw)
    out = set()

    # direct tokens
    for t in tokens:
        if t in END_MAP:
            out.add(END_MAP[t])

    # composite tokens (SXMIP / SXFIP)
    if "SXMIP" in S:
        out.update({"S", "MIP"})
    if "SXFIP" in S:
        out.update({"S", "FIP"})

    # phrase heuristics
    if any(x in S for x in ["SPIGOT X SOCKET", "SPG X SOC", "SPGXSOC", "SPIGOTXSOCKET"]):
        out.update({"SPG", "S"})
    if any(x in S for x in ["SLIP X SLIP", "SOCKET X SOCKET", "SXS", "CXC"]):
        out.add("S")

    order = ["SPG", "S", "MIP", "FIP", "CTS"]
    return [e for e in order if e in out]


def _detect_angle_deg(text: str) -> Optional[float]:
    s = canon(text)
    # explicit degree tokens
    if re.search(r"\b90(?:D|DEG)?\b", s) or " 90 " in f" {s} ":
        return 90.0
    if re.search(r"\b45(?:D|DEG)?\b", s) or " 45 " in f" {s} ":
        return 45.0
    if "22.5" in s or "22-1/2" in s:
        return 22.5
    if "11.25" in s or "11-1/4" in s:
        return 11.25
    for k, v in ANGLE_SYNONYMS.items():
        if k in s:
            return float(v)
    return None


def parse_attrs(desc: str) -> Dict:
    """Parse key attributes from a product ``desc`` string."""
    s = canon(desc)

    # ends tokens present as standalone words
    ends_tokens = [e for e in ["SXS", "CXC", "SXFIP", "SXMIP", "FIP", "MIP", "FNPT", "MNPT", "SLIP", "SOCKET", "SOC", "SPIGOT", "SPG", "CTS"] if f" {e} " in f" {s} "]
    sizes = _norm_size_combo(desc)
    angle = _detect_angle_deg(desc)

    material = next((m for m in ["CPVC", "PVC", "BRASS", "COPPER", "GALV", "SS"] if f" {m} " in f" {s} "), None)
    # Recognize DWV as material-like category (optional). If present without PVC, keep PVC and note DWV via schedule=None.
    if " DWV " in f" {s} " and material is None:
        material = "PVC"  # DWV is typically PVC; leave schedule None.

    ptype = next((t for t in ["ELBOW", "ELL", "TEE", "WYE", "COUPLING", "REDUCER", "BUSHING", "CAP", "UNION", "ADAPTER", "NIPPLE"] if f" {t} " in f" {s} "), None)
    if ptype == "ELL":
        ptype = "ELBOW"

    schedule = "SCH80" if (" SCH 80 " in f" {s} " or " SCH80 " in f" {s} ") else ("SCH40" if (" SCH 40 " in f" {s} " or " SCH40 " in f" {s} ") else None)

    attrs = {
        "material": material,
        "type": ptype,
        "schedule": schedule,
        "angle_deg": angle,
        "ends": _norm_ends(ends_tokens, desc),
        "sizes": sizes,
        "raw": desc,
        "canon": s,
    }
    return attrs


# ----------------------------
# Fast Hard-Attribute Judge
# ----------------------------

def _hard_attr_compare(a: Dict, b: Dict) -> Dict:
    """
    Return {decidable: bool, same: bool, reasons: [..]} using strict keys.
    - If any hard contradiction is found, it's a decisive False.
    - If most keys agree (>=2 of material/type/schedule + (sizes or angle present)), decisive True.
    """
    # Material
    if a["material"] and b["material"] and a["material"] != b["material"]:
        return {"decidable": True, "same": False, "reasons": ["material mismatch"]}

    # Type
    if a["type"] and b["type"] and a["type"] != b["type"]:
        return {"decidable": True, "same": False, "reasons": ["type mismatch"]}

    # Schedule
    if a["schedule"] and b["schedule"] and a["schedule"] != b["schedule"]:
        return {"decidable": True, "same": False, "reasons": ["schedule mismatch"]}

    # Angle
    A = a.get("angle_deg") or _detect_angle_deg(a["raw"])
    B = b.get("angle_deg") or _detect_angle_deg(b["raw"])
    if A and B and abs(A - B) > 0.01:
        return {"decidable": True, "same": False, "reasons": ["angle mismatch"]}

    # Ends (compare as sets of canonical tokens)
    ae = set(a.get("ends") or [])
    be = set(b.get("ends") or [])
    if ae and be and ae != be:
        return {"decidable": True, "same": False, "reasons": ["end type mismatch"]}

    # Sizes
    asz = a.get("sizes") or _norm_size_combo(a["raw"])
    bsz = b.get("sizes") or _norm_size_combo(b["raw"])
    if asz and bsz:
        if len(asz) == len(bsz) == 3:
            if Counter(asz) != Counter(bsz):
                return {"decidable": True, "same": False, "reasons": ["size mismatch"]}
        elif len(asz) == len(bsz) == 2:
            if asz != bsz and asz[::-1] != bsz:
                return {"decidable": True, "same": False, "reasons": ["size mismatch"]}
        else:
            if asz != bsz:
                return {"decidable": True, "same": False, "reasons": ["size mismatch"]}

    # If we positively have enough agreement, accept
    keys_present = sum(bool(a[k]) and bool(b[k]) for k in ("material", "type", "schedule"))
    if keys_present >= 2 and (asz or A):
        return {"decidable": True, "same": True, "reasons": []}

    return {"decidable": False, "same": False, "reasons": []}


# ----------------------------
# Web Search (Multi-provider)
# ----------------------------

def _clip_results(rows: List[Dict], k: int) -> List[Dict]:
    out = []
    for r in rows:
        title = (r.get("title") or "").strip()
        url = (r.get("url") or "").strip()
        snippet = (r.get("snippet") or "").strip()
        if url and (title or snippet):
            out.append({"title": title, "url": url, "snippet": snippet})
        if len(out) >= k:
            break
    return out


@lru_cache(maxsize=256)
def _provider_bing(query: str, k: int) -> List[Dict]:
    key = os.getenv("BING_SEARCH_KEY")
    if not key:
        return []
    try:
        resp = requests.get(
            "https://api.bing.microsoft.com/v7.0/search",
            params={"q": query, "count": k, "responseFilter": "Webpages"},
            headers={"Ocp-Apim-Subscription-Key": key},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        rows = []
        for item in (data.get("webPages", {}) or {}).get("value", []):
            rows.append({"title": item.get("name", ""), "url": item.get("url", ""), "snippet": item.get("snippet", "")})
        return _clip_results(rows, k)
    except Exception:
        return []


@lru_cache(maxsize=256)
def _provider_serpapi(query: str, k: int) -> List[Dict]:
    key = os.getenv("SERPAPI_KEY")
    if not key:
        return []
    try:
        resp = requests.get(
            "https://serpapi.com/search.json",
            params={"engine": "google", "q": query, "num": k, "api_key": key},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        rows = []
        for item in data.get("organic_results", []) or []:
            rows.append({"title": item.get("title", ""), "url": item.get("link", ""), "snippet": item.get("snippet", "")})
        return _clip_results(rows, k)
    except Exception:
        return []


@lru_cache(maxsize=256)
def _provider_google_cse(query: str, k: int) -> List[Dict]:
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")
    if not (api_key and cse_id):
        return []
    try:
        resp = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={"q": query, "cx": cse_id, "key": api_key, "num": min(k, 10)},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        rows = []
        for item in data.get("items", []) or []:
            rows.append({"title": item.get("title", ""), "url": item.get("link", ""), "snippet": item.get("snippet", "")})
        return _clip_results(rows, k)
    except Exception:
        return []


@lru_cache(maxsize=256)
def _provider_duckduckgo(query: str, k: int) -> List[Dict]:
    try:
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_redirect": 1, "no_html": 1},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        rows = []
        for item in data.get("Results", []) or []:
            rows.append({"title": item.get("Text", ""), "url": item.get("FirstURL", ""), "snippet": item.get("Text", "")})
        for topic in data.get("RelatedTopics", []) or []:
            if "Text" in topic and "FirstURL" in topic:
                rows.append({"title": topic.get("Text", ""), "url": topic.get("FirstURL", ""), "snippet": topic.get("Text", "")})
            for sub in topic.get("Topics", []) or []:
                if "Text" in sub and "FirstURL" in sub:
                    rows.append({"title": sub.get("Text", ""), "url": sub.get("FirstURL", ""), "snippet": sub.get("Text", "")})
        return _clip_results(rows, k)
    except Exception:
        return []


def web_search_snippets(query: str, k: int = 6) -> List[Dict]:
    """
    Return search snippets for ``query`` using first available provider:
    SerpAPI → Bing → Google CSE → DuckDuckGo.
    """
    for provider in (_provider_serpapi, _provider_bing, _provider_google_cse, _provider_duckduckgo):
        rows = provider(query, k)
        if rows:
            return rows[:k]
    return []


# ----------------------------
# LLM Judge
# ----------------------------

JUDGE_SYSTEM = (
    "You are a strict plumbing SKU matching assistant.\n"
    "Compare two fittings and decide if they are the SAME product.\n"
    "Use only the evidence provided (descriptions + web snippets).\n"
    "Hard constraints: Material, Type, Angle, Sizes, Schedule, Ends must agree.\n"
    "If uncertain or conflicts exist, answer false.\n"
    "Respond ONLY with valid JSON matching keys:\n"
    '{"same_product": bool, "confidence": 0..1, "blocking_reasons": [str], '
    '"key_attributes": { ... }, "best_supporting_urls": [str]}'
)


def _safe_json_loads(txt: str) -> Optional[Dict]:
    """Try to parse JSON from model text; handle fenced blocks or stray text."""
    if not txt:
        return None
    # Try direct
    try:
        return json.loads(txt)
    except Exception:
        pass
    # Try fenced ```json ... ``` extraction
    m = re.search(r"```json\s*(\{.*?\})\s*```", txt, flags=re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # Try to find the first {...} block
    m = re.search(r"(\{(?:[^{}]|(?1))*\})", txt, flags=re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    return None


def _build_query(attrs: Dict) -> str:
    """Construct a useful web query from parsed attributes."""
    parts = []
    if attrs.get("material"):
        parts.append(attrs["material"])
    if attrs.get("type"):
        parts.append(attrs["type"])
    if attrs.get("schedule"):
        parts.append(attrs["schedule"])
    if attrs.get("sizes"):
        parts.append(" X ".join(attrs["sizes"]))
    if attrs.get("ends"):
        parts.extend(attrs["ends"])
    # include full canon at the end to give more context
    parts.append(attrs.get("canon", ""))
    q = " ".join(x for x in parts if x).strip()
    # squeeze spaces
    q = re.sub(r"\s+", " ", q)
    return q


def judge_same_product(desc_a: str, desc_b: str, use_web: bool = True, max_snippets: int = 8) -> Dict:
    """
    Judge whether two descriptions refer to the same product.

    Args:
        desc_a: supplier A description
        desc_b: supplier B description
        use_web: if False, skip web search and judge from attributes + (optional) LLM
        max_snippets: cap for web snippets passed to the LLM (total from A+B queries)

    Returns:
        Dict with keys:
        - same_product (bool)
        - confidence (float in [0,1])
        - blocking_reasons (List[str])
        - key_attributes (Dict[str, Any])
        - best_supporting_urls (List[str])
    """
    a = parse_attrs(desc_a)
    b = parse_attrs(desc_b)

    # 1) Quick hard-attribute judge
    quick = _hard_attr_compare(a, b)
    if quick["decidable"]:
        return {
            "same_product": quick["same"],
            "confidence": 0.95 if quick["same"] else 0.99,
            "blocking_reasons": quick["reasons"],
            "key_attributes": {"A": a, "B": b},
            "best_supporting_urls": [],
        }

    # 2) Optional web RAG
    snippets: List[Dict] = []
    if use_web:
        q_a = _build_query(a)
        q_b = _build_query(b)
        # split budget between A and B queries
        half = max(1, max_snippets // 2)
        snippets = web_search_snippets(q_a, k=half) + web_search_snippets(q_b, k=max_snippets - half)

    # 3) If still no web evidence, we can either
    #    a) Ask LLM to judge from attributes alone (lower confidence)
    #    b) Or return undecided low-confidence
    # We'll ask the LLM; if the LLM fails, fall back to undecided.
    user_prompt = textwrap.dedent(
        f"""
        A description: {a['raw']}
        A parsed: {json.dumps({k: v for k, v in a.items() if k != 'raw'}, ensure_ascii=False)}

        B description: {b['raw']}
        B parsed: {json.dumps({k: v for k, v in b.items() if k != 'raw'}, ensure_ascii=False)}

        Web snippets (title | url | snippet):
        {json.dumps(snippets[:max_snippets], ensure_ascii=False, indent=2)}

        Decide if A and B are the SAME product. Follow hard constraints.
        Output JSON only.
        """
    ).strip()

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
        )
        txt = (resp.choices[0].message.content or "").strip()
        data = _safe_json_loads(txt)
        if not isinstance(data, dict) or "same_product" not in data:
            raise ValueError("Model did not return valid JSON.")
        # inject parsed attrs if model omitted them
        if "key_attributes" not in data or not isinstance(data["key_attributes"], dict):
            data["key_attributes"] = {"A": a, "B": b}
        # best_supporting_urls: ensure list[str]
        urls = data.get("best_supporting_urls") or []
        if not isinstance(urls, list):
            urls = []
        # if empty and we had snippets, pick a few from snippets
        if not urls and snippets:
            urls = [s["url"] for s in snippets if s.get("url")][:3]
        data["best_supporting_urls"] = urls
        # Ensure blocking_reasons present
        if "blocking_reasons" not in data or not isinstance(data["blocking_reasons"], list):
            data["blocking_reasons"] = []
        return data
    except Exception:
        # Fallback: undecided based on attributes only
        return {
            "same_product": False,
            "confidence": 0.5 if not snippets else 0.6,
            "blocking_reasons": ["LLM judging error or invalid JSON"],
            "key_attributes": {"A": a, "B": b},
            "best_supporting_urls": [s["url"] for s in snippets[:3] if s.get("url")] if snippets else [],
        }


__all__ = ["judge_same_product", "parse_attrs", "canon", "web_search_snippets"]
