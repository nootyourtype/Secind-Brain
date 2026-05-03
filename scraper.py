import os
import re
import requests
from bs4 import BeautifulSoup
from ingest import NOTES_DIR

def fetch_and_save_url(url: str):
    """
    Fetches the content of a URL, cleans the HTML, 
    and saves it as a text file in NOTES_DIR for auto-ingestion.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, 'html.parser')

    # Extract title
    title = soup.title.get_text(strip=True) if soup.title else "Untitled_Webpage"
    safe_title = re.sub(r'[\/\\\:\*\?\"\<\>\|]', '_', title)[:50].strip()
    
    # Remove script, style, navigation, footers to isolate main content
    for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
        element.decompose()

    # Get text
    text = soup.get_text(separator="\n")
    
    # Clean up empty lines
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    cleaned_text = '\n'.join(chunk for chunk in chunks if chunk)

    file_name = f"web_{safe_title}.txt"
    file_path = os.path.join(NOTES_DIR, file_name)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"Source URL: {url}\nTitle: {title}\n\n")
        f.write(cleaned_text)

    return file_name

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        fname = fetch_and_save_url(sys.argv[1])
        print(f"Saved to {fname}")
