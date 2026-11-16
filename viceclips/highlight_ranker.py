"""Gemini-assisted highlight selection from timestamped speech.

The model ranks transcript moments for hooks, reactions, tension, surprise and payoff.
It does not inspect gameplay pixels; visual/audio event analysis is a separate future layer.
"""
import json
import os
import re
import urllib.error
import urllib.request


MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    + MODEL
    + ":generateContent"
)


def _request_gemini(prompt):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing; add it to repository Actions secrets.")
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2,
        },
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1200]
        raise RuntimeError(f"Gemini API returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach Gemini API: {exc}") from exc

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        result = json.loads(text)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Gemini returned an invalid highlight-ranking response.") from exc
    if not isinstance(result, dict) or not isinstance(result.get("highlights"), list):
        raise RuntimeError("Gemini response did not contain a highlights array.")
    return result["highlights"]


def rank_highlights(rows, duration, clip_len=35.0, max_results=5):
    """Ask Gemini to rank timestamped transcript moments across the whole video."""
    if not rows:
        raise RuntimeError("No transcript was available for AI highlight ranking.")

    # Send transcript in bounded time windows so long recordings are not truncated.
    chunk_seconds = 8 * 60
    chunks = {}
    for start, end, word in rows:
        bucket = int(max(0, start) // chunk_seconds)
        chunks.setdefault(bucket, []).append((start, end, word))

    ranked = []
    for bucket, chunk_rows in sorted(chunks.items()):
        chunk_start = bucket * chunk_seconds
        chunk_end = min(duration, chunk_start + chunk_seconds)
        transcript = "\n".join(
            f"[{start:.1f}-{end:.1f}] {word}" for start, end, word in chunk_rows
        )
        prompt = f"""
You are an expert gaming-video Shorts editor. Rank moments from this GTA gameplay
commentary transcript. Prefer surprising gameplay events, funny or intense reactions,
unexpected outcomes, strong hooks, tension/payoff, and moments understandable without
long setup. Do NOT reward ordinary narration or simply dense speech.

The transcript timestamps are seconds from the start of the ORIGINAL video.
Analyze only this segment: {chunk_start:.1f} to {chunk_end:.1f} seconds.
Each selected clip should be {clip_len:.0f} seconds or less, and must stay inside
this segment. Return up to 2 distinct moments. If no compelling moment exists, return
an empty list. Never invent events that are not supported by the transcript.

Return JSON only:
{{"highlights":[{{"start_seconds":123.0,"score":0-100,
"hook":"short opening hook","reason":"why this is compelling"}}]}}
Scores should reflect likely viewer retention, not transcript word count.

TRANSCRIPT:
{transcript}
"""
        for item in _request_gemini(prompt):
            try:
                start = float(item["start_seconds"])
                score = float(item["score"])
                hook = str(item.get("hook", "")).strip()[:180]
                reason = str(item.get("reason", "")).strip()[:300]
            except (KeyError, TypeError, ValueError):
                continue
            if chunk_start <= start < chunk_end and 0 <= score <= 100:
                start = max(0.0, min(start, max(0.0, duration - clip_len)))
                ranked.append({
                    "start": start,
                    "score": score,
                    "hook": hook,
                    "reason": reason,
                })

    # Deduplicate suggestions whose starts are within 20 seconds.
    ranked.sort(key=lambda item: item["score"], reverse=True)
    unique = []
    for candidate in ranked:
        if all(abs(candidate["start"] - chosen["start"]) >= 20 for chosen in unique):
            unique.append(candidate)
        if len(unique) >= max_results:
            break
    if not unique:
        raise RuntimeError("Gemini found no usable highlight candidates in the transcript.")
    return unique
