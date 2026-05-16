#!/usr/bin/env python3
"""Fetch YouTube transcript via youtube-transcript-api. Output JSON to stdout."""
import sys
import json

if len(sys.argv) < 2:
    print(json.dumps({"error": "Usage: get_transcript.py <video_id>"}))
    sys.exit(1)

video_id = sys.argv[1]

try:
    # Suppress urllib3 warning about LibreSSL
    import warnings
    warnings.filterwarnings("ignore")

    from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

    api = YouTubeTranscriptApi()
    try:
        transcript = api.fetch(video_id, languages=["en"])
    except NoTranscriptFound:
        # Try auto-generated
        tl = api.list(video_id)
        transcript = tl.find_generated_transcript(["en"]).fetch()

    snippets = list(transcript)
    full_text = " ".join(s.text for s in snippets).strip()

    print(json.dumps({
        "video_id": video_id,
        "word_count": len(full_text.split()),
        "transcript": full_text
    }))

except Exception as e:
    print(json.dumps({"error": str(e), "video_id": video_id}))
    sys.exit(1)
