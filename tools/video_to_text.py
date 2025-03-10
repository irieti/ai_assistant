import os
from googleapiclient.discovery import build
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
)
import json
from dotenv import load_dotenv


load_dotenv()

# Define your API key and the YouTube API service
API_KEY = os.getenv("YOUTUBE_API_KEY")
print(f"API_KEY: {API_KEY}")
youtube = build("youtube", "v3", developerKey=API_KEY)

# Path configurations
VIDEO_FOLDER = "videos"
PROCESSED_FOLDER = "videos/processed"
KNOWLEDGE_BASE_FOLDER = "knowledge_base"
VIDEO_JSON_PATH = os.path.join(VIDEO_FOLDER, "video_ids.json")

os.makedirs(PROCESSED_FOLDER, exist_ok=True)
os.makedirs(KNOWLEDGE_BASE_FOLDER, exist_ok=True)


def get_video_metadata(video_id):
    try:
        request = youtube.videos().list(part="snippet", id=video_id)
        response = request.execute()
        if response["items"]:
            item = response["items"][0]
            return {
                "title": item["snippet"]["title"],
                "description": item["snippet"]["description"],
            }
        print(f"No metadata found for video ID: {video_id}")
    except Exception as e:
        print(f"Error retrieving metadata for video ID {video_id}: {e}")
    return None


def get_video_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = transcript_list.find_generated_transcript(
            ["ru"]
        )  # Change language if needed
        return " ".join([entry["text"] for entry in transcript.fetch()])
    except (NoTranscriptFound, TranscriptsDisabled) as e:
        print(f"Transcript issue for video {video_id}: {e}")
    except Exception as e:
        print(f"Could not retrieve transcript for video {video_id}: {e}")
    return None


def video_to_text(video_id):
    metadata = get_video_metadata(video_id)
    transcript = get_video_transcript(video_id)
    if metadata and transcript:
        video_name = f"{video_id}.txt"
        output_path = os.path.join(KNOWLEDGE_BASE_FOLDER, video_name)
        with open(output_path, "w", encoding="utf-8") as file:
            file.write(f"Title: {metadata['title']}\n\n")
            file.write(f"Description: {metadata['description']}\n\n")
            file.write(f"Transcript:\n{transcript}")
        return output_path
    return None


def process_new_videos():
    if not os.path.exists(VIDEO_JSON_PATH):
        print("No video JSON file found.")
        return

    with open(VIDEO_JSON_PATH, "r", encoding="utf-8") as file:
        video_data = json.load(file)

    for video_id in video_data.get("video_ids", []):
        output_path = os.path.join(KNOWLEDGE_BASE_FOLDER, f"{video_id}.txt")
        if not os.path.exists(output_path):
            print(f"Processing new video: {video_id}")
            video_to_text(video_id)
