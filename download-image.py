import sqlite3
import os
import re
import sys
import argparse
import requests
import html
from urllib.parse import urlparse, parse_qs, unquote
from dotenv import load_dotenv

load_dotenv()

SOURCE_URL = os.getenv("SOURCE_URL", "https://some-url")
DB_PATH = "./learning_platform.db"
DOWNLOAD_DIR = "./uploads/downloaded"


def resolve_url(url):
    url = html.unescape(url)
    parsed = urlparse(url)
    if parsed.path == "/_next/image":
        qs = parse_qs(parsed.query)
        if "url" in qs:
            raw_path = unquote(qs["url"][0])
            return f"{SOURCE_URL}{raw_path}"
    return url


def download_image(url, save_path):
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    with open(save_path, "wb") as f:
        f.write(response.content)
    print(f"    Downloaded: {url} -> {save_path}")


def process_lesson(cursor, lesson_id, log_file):
    cursor.execute(
        "SELECT id, slug, title, content FROM lessons WHERE id = ?",
        (lesson_id,),
    )
    lesson = cursor.fetchone()
    if not lesson:
        print(f"  Lesson {lesson_id} not found.")
        return 0

    print(f"\n  Processing lesson {lesson['id']}: {lesson['title']}")
    content = lesson["content"] or ""
    base = re.escape(SOURCE_URL)
    image_pattern = re.compile(rf"{base}/[^\s\"'<>\)]+")
    urls = image_pattern.findall(content)
    urls = list(dict.fromkeys(urls))

    if not urls:
        print("    No images found.")
        return 0

    print(f"    Found {len(urls)} image(s)")
    downloaded = 0
    for url in urls:
        resolved_url = resolve_url(url)
        parsed = urlparse(resolved_url)
        filename = os.path.basename(parsed.path)
        if not filename or "." not in filename:
            print(f"    No extension, logged: {resolved_url}")
            log_file.write(f"{resolved_url}\n")
            log_file.flush()
            continue
        save_path = os.path.join(DOWNLOAD_DIR, filename)

        if os.path.exists(save_path):
            print(f"    Already exists, skipping: {filename}")
            continue

        try:
            download_image(resolved_url, save_path)
            downloaded += 1
        except Exception as e:
            print(f"    Failed to download {resolved_url}: {e}")

    return downloaded


def parse_lesson_range(range_str):
    parts = range_str.split("-")
    if len(parts) == 1:
        return [int(parts[0])]
    return list(range(int(parts[0]), int(parts[1]) + 1))


def main():
    parser = argparse.ArgumentParser(description="Download images from lesson content")
    parser.add_argument(
        "--lesson-ids",
        type=str,
        required=True,
        help="Lesson ID range (e.g., 1-10, 5, 15-20)",
    )
    args = parser.parse_args()

    lesson_ids = parse_lesson_range(args.lesson_ids)

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    log_path = os.path.join(DOWNLOAD_DIR, "log.txt")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    total_downloaded = 0
    with open(log_path, "a") as log_file:
        for lesson_id in lesson_ids:
            total_downloaded += process_lesson(cursor, lesson_id, log_file)

    conn.close()
    print(f"\nBatch complete. Total downloaded: {total_downloaded} image(s)")


if __name__ == "__main__":
    main()
