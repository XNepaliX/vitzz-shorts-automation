# ViceClips full engine: PeakCut setup

ViceClips now pins the upstream PeakCut project as a Git submodule at
`viceclips/peakcut-upstream`. The pinned upstream commit is
`b3e403e27444b620a50a4ec1cf44b3afff9e9e45` so the engine does not silently change underneath this project.

PeakCut is the full application for long-video and live-stream clipping. It provides
rolling stream recording, transcript/loudness/chat-based highlight decisions,
9:16 rendering, word-level captions, creator workspaces and connected-platform
posting. Its source remains in the upstream submodule rather than being copied
and modified in this repository.

## Get the source

From a computer or Linux server with Git:

```bash
git clone https://github.com/XNepaliX/vitzz-shorts-automation.git
cd vitzz-shorts-automation
git submodule update --init --recursive
cd viceclips/peakcut-upstream
```

If you already cloned the repository, run only:

```bash
git submodule update --init --recursive
```

## Run locally

Requirements: Python 3.10+, FFmpeg, and a persistent machine. PeakCut's
quick-start is:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m studio.server
```

Then open `http://127.0.0.1:8765` on that same machine. The first start
downloads its speech-recognition model (about 480 MB). In Settings → AI, add
an AI provider key if you want semantic AI clip selection; without one, PeakCut
can still select by loudness.

## Persistent server deployment

For a public, always-on service, follow the upstream `DEPLOY.md` and
`docker-compose.yml`. The upstream deployment guide recommends a Linux
server with 8+ CPU cores, 16 GB RAM and 200+ GB disk for multiple users.
A domain, HTTPS, and an AI provider key are also needed. Connecting YouTube
requires a Google OAuth web client and YouTube Data API v3. Public API uploads
may remain private until Google's API audit is completed.

GitHub Actions is not the server: its runners are temporary and cannot keep
live recordings or the dashboard running between jobs. The existing
`viceclips-private-test.yml` remains a separate, manual batch-test path.

## Safety and publishing

- No PeakCut account has been connected by this repository change.
- No YouTube OAuth credentials or AI keys are included.
- Do not add secrets to Git; use PeakCut's Settings page or untracked environment files.
- Keep automatic posting disabled until the correct ViceClips account is connected
  and a private test has been reviewed.
- Only capture or reuse streams/videos you own or have permission to use.
- This repository's short-form test pipeline never publishes; it only saves an artifact.

## Update the pinned engine

Update only after reviewing upstream changes and rerunning tests:

```bash
cd viceclips/peakcut-upstream
git fetch origin
git checkout <reviewed-commit>
cd ../..
git add viceclips/peakcut-upstream
git commit -m "Update pinned PeakCut engine"
```

PeakCut is MIT-licensed upstream. Keep its upstream license and notices with
the submodule when distributing it.
