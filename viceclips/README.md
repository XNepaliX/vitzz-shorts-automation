# ViceClips private highlight test

This workflow downloads a source URL that you own or are explicitly permitted to reuse,
transcribes it with local Whisper, asks Gemini to rank timestamped transcript moments,
and renders the highest-ranked moment as a vertical captioned MP4.

## Configure
Add a GitHub Actions repository secret named `GEMINI_API_KEY`.
The workflow uses `gemini-3.5-flash` by default; set `GEMINI_MODEL` in the workflow
if you want to select another compatible model.

## Run
Open Actions → "ViceClips — make a private AI-ranked test clip" → Run workflow.
Provide the source URL and confirm reuse permission. The result is saved as a private
GitHub Actions artifact for 7 days.

## Important limits
- Gemini ranks transcript moments for hooks, reactions, tension, surprise and payoff.
- This first AI pass does not inspect gameplay frames or detect non-verbal events.
- It creates one top-ranked clip, not a batch of Shorts.
- It never uploads to YouTube. Review the MP4 and report before any separate publishing step.
- Gemini API usage may be subject to free-tier quotas and rate limits.
