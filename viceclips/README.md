# ViceClips — private clip pipeline

This folder is isolated from the existing channel workflow. It adds no channel name, watermark, or branding to rendered videos.

## Current phase

A manually triggered GitHub Actions job accepts one source video URL, downloads it, transcribes it, selects a speech-dense 35-second window using an efficient interval sweep, renders a 9:16 MP4 with burned-in captions, and uploads the result as a private workflow artifact. The subtitle path is resolved from the selected output folder.

- No YouTube publishing or account connection.
- No automatic public posting.
- The source must be yours or explicitly licensed for reuse. Confirm this in the workflow input before running.
- GitHub-hosted runners are temporary; artifacts are retained for 7 days.
- This is a lightweight batch pipeline, not the full PeakCut live-stream system. It does not monitor or capture streams continuously.
- A separate CI workflow runs Python syntax checks, unit tests for highlight-window selection, and a synthetic FFmpeg render test. It does not download a real stream or publish anything.

## Full live-clipping engine

The upstream PeakCut application is pinned as a Git submodule at `viceclips/peakcut-upstream`. Follow [PEAKCUT_SETUP.md](PEAKCUT_SETUP.md) to fetch and run it on a persistent computer or server. The submodule provides the full live-stream dashboard and clipping engine; the GitHub Actions pipeline below remains a separate temporary batch-test path.

## Run

1. Open the repository's **Actions** tab.
2. Choose **ViceClips — make a private test clip**.
3. Select **Run workflow**.
4. Paste a source URL you own or have permission to reuse.
5. Set the rights confirmation to **yes**.
6. Wait for the job, then download the `viceclips-test` artifact.

The first run may take several minutes because it installs video and speech-processing dependencies. YouTube may block downloads from cloud runner IP addresses; if that happens, use an authorized direct video file instead (direct-file input support can be added next).

## Validation

The CI test workflow runs automatically when files under `viceclips/` change. It creates a synthetic two-second video, burns in a test subtitle, and checks that the output is 1080×1920. It also compares the optimized clip-window selector against a brute-force reference on a deterministic sample.

## Limits

This is a batch test, not continuous live clipping. GitHub Actions is not a persistent video server, and long videos can exceed runner time or storage limits. The current clip selection prioritizes speech density; it is not yet a semantic GTA highlight detector. Review every clip before publishing.
