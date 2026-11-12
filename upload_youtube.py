import os, sys
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

video = Path(sys.argv[1])
part = int(os.environ["PART"])
client_id = os.environ["YT_CLIENT_ID"]
client_secret = os.environ["YT_CLIENT_SECRET"]
refresh_token = os.environ["YT_REFRESH_TOKEN"]
if not video.is_file() or video.stat().st_size < 100_000:
    raise SystemExit(f"Refusing upload: missing or suspiciously small file: {video}")
creds = Credentials(
    token=None,
    refresh_token=refresh_token,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=client_id,
    client_secret=client_secret,
    scopes=["https://www.googleapis.com/auth/youtube.upload"],
)
creds.refresh(Request())
youtube = build("youtube", "v3", credentials=creds)
titles = {
    1: "The Girl in Room 309 | Part 1: The 3:07 AM Call #Shorts",
    2: "The Girl in Room 309 | Part 2: You Died Here #Shorts",
}
descriptions = {
    1: "At 3:07 AM, Arjun receives a call from his own number. The warning changes everything. Fictional horror story. Part 1.",
    2: "The truth behind Room 309 is finally revealed. Fictional horror story. Part 2.",
}
body = {
    "snippet": {
        "title": titles[part],
        "description": descriptions[part],
        "categoryId": "24",
        "tags": ["horror", "short horror story", "scary story", "shorts"],
    },
    "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
}
media = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
response = None
while response is None:
    status, response = request.next_chunk()
    if status:
        print(f"Upload progress: {int(status.progress() * 100)}%")
if not response or not response.get("id"):
    raise RuntimeError(f"YouTube did not return a video ID: {response}")
print(f"PUBLIC_VIDEO_URL=https://www.youtube.com/shorts/{response['id']}")
