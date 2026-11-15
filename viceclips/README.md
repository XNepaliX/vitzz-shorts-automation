# ViceClips — private clip pipeline

This folder is isolated from the existing channel workflow. It adds no channel name, watermark, or branding to rendered videos.

## Current phase

A manually triggered GitHub Actions job accepts one source video URL, downloads it, transcribes it, selects a speech-dense 35-second window, renders a 9:16 MP4 with burned-in captions, and uploads the result as a private workflow artifact.

- No YouTube publishing or account connection.
- No automatic public posting.
- The source must be yours or explicitly licensed for reuse. Confirm this in the workflow input before running.
- GitHub-hosted runners are temporary; artifacts are retained for 7 days.
- This is a lightweight first processing stage, not the full PeakCut live-stream system. It does not monitor or capture streams continuously.

## Run

1. Open the repository's **Actions** tab.
2. Choose **ViceClips — make a private test clip**.
3. Select **Run workflow**.
4. Paste a source URL you own or have permission to reuse.
5. Set the rights confirmation to **yes**.
6. Wait for the job, then download the `viceclips-test` artifact.

The first run may take several minutes because it installs video and speech-processing dependencies. YouTube may block downloads from cloud runner IP addresses; if that happens, use an authorized direct video file instead (direct-file input support can be added next).

## Limits

This is a batch test, not continuous live clipping. GitHub Actions is not a persistent video server, and long videos can exceed runner time or storage limits. The current clip selection prioritizes speech density; it is not yet a semantic GTA highlight detector. Review every clip before publishing.
