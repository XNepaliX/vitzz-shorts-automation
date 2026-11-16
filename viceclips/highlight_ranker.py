"""AI highlight ranking for timestamped speech.

OpenAI is preferred when OPENAI_API_KEY is configured; Gemini is the fallback.
This is transcript-context ranking, not visual gameplay understanding.
"""
import json
import os
import urllib.error
import urllib.request


def _post_json(url, headers, payload, provider):
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers}, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"{provider} API HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{provider} API connection failed: {exc}") from exc


def _request_openai(prompt):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is missing.")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    data = _post_json(
        "https://api.openai.com/v1/chat/completions",
        {"Authorization": f"Bearer {key}"},
        {"model": model, "messages": [
            {"role": "system", "content": "You are a gaming Shorts editor. Return valid JSON only."},
            {"role": "user", "content": prompt}],
         "response_format": {"type": "json_object"}, "temperature": 0.2},
        "OpenAI"
    )
    try:
        result = json.loads(data["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("OpenAI returned malformed JSON.") from exc
    if not isinstance(result, dict) or not isinstance(result.get("highlights"), list):
        raise RuntimeError("OpenAI response lacks a highlights array.")
    return result["highlights"]


def _request_gemini(prompt):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is missing.")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    data = _post_json(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        {"x-goog-api-key": key},
        {"contents": [{"parts": [{"text": prompt}]}],
         "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}},
        "Gemini"
    )
    try:
        result = json.loads(data["candidates"][0]["content"]["parts"][0]["text"])
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Gemini returned malformed JSON.") from exc
    if not isinstance(result, dict) or not isinstance(result.get("highlights"), list):
        raise RuntimeError("Gemini response lacks a highlights array.")
    return result["highlights"]


def _request_ai(prompt):
    if os.getenv("OPENAI_API_KEY"):
        return _request_openai(prompt), "OpenAI"
    if os.getenv("GEMINI_API_KEY"):
        return _request_gemini(prompt), "Gemini"
    raise RuntimeError("Add OPENAI_API_KEY or GEMINI_API_KEY to GitHub Actions secrets.")


def rank_highlights(rows, duration, clip_len=35.0, max_results=5):
    if not rows:
        raise RuntimeError("No transcript was available for AI highlight ranking.")
    chunks = {}
    for start, end, word in rows:
        chunks.setdefault(int(max(0, start) // 480), []).append((start, end, word))
    ranked, provider_used = [], None
    for bucket, chunk_rows in sorted(chunks.items()):
        lo, hi = bucket * 480, min(duration, (bucket + 1) * 480)
        transcript = "\n".join(f"[{s:.1f}-{e:.1f}] {w}" for s, e, w in chunk_rows)
        prompt = f"""
Rank the most compelling GTA gameplay moments for YouTube Shorts using this transcript.
Prioritize surprising outcomes, funny/intense reactions, tension/payoff and strong hooks.
Do not reward ordinary narration or word density alone. Do not invent visual events.
Timestamps are seconds in the ORIGINAL video. Choose moments inside {lo:.1f}-{hi:.1f}s.
Return up to 2 distinct candidates, each no longer than {clip_len:.0f}s.
Return JSON only: {{"highlights":[{{"start_seconds":123.0,"score":87,
"hook":"brief opening hook","reason":"why this moment retains viewers"}}]}}
If no strong moment is supported, return an empty highlights array.
TRANSCRIPT:
{transcript}
"""
        items, provider = _request_ai(prompt)
        provider_used = provider
        for item in items:
            try:
                start = float(item["start_seconds"])
                score = float(item["score"])
            except (KeyError, TypeError, ValueError):
                continue
            if lo <= start < hi and 0 <= score <= 100:
                start = min(max(0.0, start), max(0.0, duration - clip_len))
                ranked.append({"start": start, "score": score,
                               "hook": str(item.get("hook", ""))[:180],
                               "reason": str(item.get("reason", ""))[:300],
                               "provider": provider})
    ranked.sort(key=lambda x: x["score"], reverse=True)
    unique = []
    for candidate in ranked:
        if all(abs(candidate["start"] - old["start"]) >= 20 for old in unique):
            unique.append(candidate)
        if len(unique) >= max_results:
            break
    if not unique:
        raise RuntimeError("AI found no usable highlight candidates in the transcript.")
    return unique
