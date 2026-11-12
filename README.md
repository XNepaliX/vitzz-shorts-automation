# Automated Horror Short

A GitHub Actions workflow renders a 15-second vertical 9:16 horror Short with English AI narration, burned-in captions, and subtle rain ambience.

## Run
- Open the **Actions** tab.
- Select **Create horror Short**.
- Choose **Run workflow**.
- Download the `horror-short` artifact from the completed run.

The workflow also runs automatically when `video.py` or this workflow changes on `main`.

No channel branding is added. This workflow builds a video artifact; it does not publish to YouTube. YouTube publishing requires a separately configured YouTube API OAuth credential and explicit upload settings.
