"""AI-assisted highlight selection from timestamped speech.

Uses OpenAI when OPENAI_API_KEY is configured; otherwise uses Gemini.
The model ranks transcript moments, but does not inspect gameplay pixels.
"""
import json
import os
import urllib.error
import urllib.request


def _post_json(url, headers, payload, provider):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1200]
        raise RuntimeError(f"{provider} API returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach {provider} API: {exc}") from exc
    return data


def _request_openai(prompt):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing.")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    data = _post_json(
        "https://api.openai.com/v1/chat/completions",
        {"Authorization": f"Bearer {api_key}"},
        {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are an expert gaming-video Shorts editor. Return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        },
        "OpenAI",
    )
    try:
        result = json.loads(data["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("OpenAI returned an invalid highlight-ranking response.") from exc
    if not isinstance(result, dict) or not isinstance(result.get("highlights"), list):
        raise RuntimeError("OpenAI response did not contain a highlights array.")
    return result["highlights"]


def _request_gemini(prompt):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing; add it to repository Actions secrets.")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    data = _post_json(
        url,
        {"x-goog-api-key": api_key},
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2,
            },
        },
        "Gemini",
    )
    try:
        result = json.loads(data["candidates"][0]["content"]["parts"][0]["text"])
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Gemini returned an invalid highlight-ranking response.") from exc
    if not isinstance(result, dict) or not isinstance(result.get("highlights"), list):
        raise RuntimeError("Gemini response did not contain a highlights array.")
    return result["highlights"]


def _request_ai(prompt):
    # Prefer OpenAI when configured; keep Gemini as the no-OpenAI fallback.
    if os.getenv("OPENAI_API_KEY"):
        return _request_openai(prompt), "OpenAI"
    if os.getenv("GEMINI_API_KEY"):
        return _request_gemini(prompt), "Gemini"
    raise RuntimeError("Add OPENAI_API_KEY or GEMINI_API_KEY to repository Actions secrets.")


def rank_highlights(rows, duration, clip_len=35.0, max_results=5):
    """Rank timestamped transcript moments across the full source video."""
    if not rows:
        raise RuntimeError("No transcript was available for AI highlight ranking.")

    chunk_seconds = 8 * 60
    chunks = {}
    for start, end, word in rows:
        bucket = int(max(0, start) // chunk_seconds)
        chunks.setdefault(bucket, []).append((start, end, word))

    ranked = []
    provider_used = None
    for bucket, chunk_rows in sorted(chunks.items()):
        chunk_start = bucket * chunk_seconds
        chunk_end = min(duration, chunk_start + chunk_seconds)
        transcript = "\n".join(
            f"[{start:.1f}-{end:.1f}] {word}" for start, end, word in chunk_rows
        )
        prompt = f"""
Rank moments from this GTA gameplay commentary transcript for YouTube Shorts.
Prefer surprising gameplay events, funny or intense reactions, unexpected outcomes,
strong hooks, tension/payoff, and moments understandable without long setup.
Do NOT reward ordinary narration or simply dense speech.

Timestamps are seconds from the ORIGINAL video. Analyze only {chunk_start:.1f}
to {chunk_end:.1f} seconds. Each selected clip must be {clip_len:.0f} seconds or
less and stay inside this segment. Return up to 2 distinct moments. If no compelling
moment exists, return an empty list. Never invent events not supported by the transcript.

Return JSON only:
{{"highlights":[{{"start_seconds":123.0,"score":85,
"hook":"short opening hook","reason":"why this is compelling"}}]}}
Score likely viewer retention, not transcript word count.

TRANSCRIPT:
{transcript}
"""
        items, provider = _request_ai(prompt)
        provider_used = provider
        for item in items:
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
                    "provider": provider,
                })

    ranked.sort(key=lambda item: item["score"], reverse=True)
    unique = []
    for candidate in ranked:
        if all(abs(candidate["start"] - chosen["start"]) >= 20 for chosen in unique):
            unique.append(candidate)
        if len(unique) >= max_results:
            break
    if not unique:
        raise RuntimeError("AI found no usable highlight candidates in the transcript.")
    return unique
