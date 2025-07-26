import gspread
import pandas as pd
from googleapiclient.discovery import build
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import time
import re
import os
import json
import logging
from datetime import datetime
import sys

# Import your LLM client library
import google.generativeai as genai

# Load configurations
from config import (
    GOOGLE_SHEETS_SERVICE_ACCOUNT_FILE,
    YOUTUBE_API_KEY,
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    LLM_API_KEY
)


# Setup logging
def setup_logging():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"music_processor_log_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return log_filename


# Interactive input functions
def get_user_inputs():
    """Get user inputs for spreadsheet, worksheet, and row range"""
    print("=== Music Data Processor Setup ===")

    # Get spreadsheet ID
    spreadsheet_id = input("Enter Google Sheets Spreadsheet ID: ").strip()
    if not spreadsheet_id:
        print("Error: Spreadsheet ID is required")
        sys.exit(1)

    # Get worksheet name
    worksheet_name = input("Enter Worksheet name (default: 'Cleaned_Songs_Data'): ").strip()
    if not worksheet_name:
        worksheet_name = 'Cleaned_Songs_Data'

    # Get row range
    print("Enter row range to process:")
    start_row = input("Start row (default: 2): ").strip()
    start_row = int(start_row) if start_row else 2

    end_row = input("End row (leave empty for all rows): ").strip()
    end_row = int(end_row) if end_row else None

    # Get batch size
    batch_size = input("Batch size for LLM processing (default: 5): ").strip()
    batch_size = int(batch_size) if batch_size else 5

    return spreadsheet_id, worksheet_name, start_row, end_row, batch_size


def initialize_apis(spreadsheet_id, worksheet_name):
    """Initialize all API clients"""
    try:
        # Google Sheets
        gc = gspread.service_account(filename=GOOGLE_SHEETS_SERVICE_ACCOUNT_FILE)
        spreadsheet = gc.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet(worksheet_name)
        logging.info("Successfully connected to Google Sheet.")

        # YouTube API
        youtube_service = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        logging.info("YouTube API client initialized.")

        # Spotify API
        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET
        ))
        logging.info("Spotify API client initialized.")

        # LLM Client
        genai.configure(api_key=LLM_API_KEY)
        llm_model = genai.GenerativeModel('gemini-1.5-pro')
        logging.info("LLM client initialized.")

        return worksheet, youtube_service, sp, llm_model

    except Exception as e:
        logging.error(f"Error initializing APIs: {e}")
        sys.exit(1)


# Enhanced helper functions with version detection
def get_youtube_metadata_from_url(url, youtube_service):
    """Extracts artist, title, and version info from a YouTube video URL."""
    if not url or "youtube.com/watch?v=" not in url:
        return None, None, None

    video_id_match = re.search(r"v=([^&]+)", url)
    if not video_id_match:
        return None, None, None

    video_id = video_id_match.group(1)

    try:
        request = youtube_service.videos().list(part="snippet", id=video_id)
        response = request.execute()

        if response and response['items']:
            snippet = response['items'][0]['snippet']
            title = snippet.get('title', '')
            channel_title = snippet.get('channelTitle', '')

            # Detect version type from title
            version_type = detect_version_type(title)

            return channel_title, title, version_type
        return None, None, None

    except Exception as e:
        logging.error(f"Error fetching YouTube metadata for {url}: {e}")
        return None, None, None


def get_spotify_metadata_from_url(url, sp):
    """Extracts artist, title, and version info from a Spotify track URL."""
    if not url or "open.spotify.com/track/" not in url:
        return None, None, None

    track_id_match = re.search(r"track/([^?]+)", url)
    if not track_id_match:
        return None, None, None

    track_id = track_id_match.group(1)

    try:
        track_info = sp.track(track_id)
        if track_info:
            artist_name = track_info['artists'][0]['name'] if track_info['artists'] else None
            song_title = track_info['name']
            album_name = track_info['album']['name'] if track_info['album'] else ''

            # Detect version type from title and album
            version_type = detect_version_type(song_title, album_name)

            return artist_name, song_title, version_type
        return None, None, None

    except Exception as e:
        logging.error(f"Error fetching Spotify metadata for {url}: {e}")
        return None, None, None


def detect_version_type(title, album_name=''):
    """Detect version type from title and album information"""
    title_lower = title.lower()
    album_lower = album_name.lower()

    # Check for various version indicators
    if any(indicator in title_lower for indicator in ['live', 'concert', 'tour']):
        return 'Live'
    elif any(indicator in title_lower for indicator in ['remix', 'mix', 'edit']):
        return 'Remix'
    elif any(indicator in title_lower for indicator in ['acoustic', 'unplugged']):
        return 'Acoustic'
    elif any(indicator in title_lower for indicator in ['cover', 'version']):
        return 'Cover'
    elif any(indicator in title_lower for indicator in ['karaoke', 'instrumental']):
        return 'Instrumental'
    elif any(indicator in title_lower for indicator in ['remaster', 'remastered']):
        return 'Remastered'
    elif 'live' in album_lower or 'concert' in album_lower:
        return 'Live'
    else:
        return 'Original'


def search_youtube_with_version(artist, song_title, youtube_client, preferred_version='Original'):
    """Enhanced YouTube search with version preference"""
    base_query = f"{artist} - {song_title}"

    # Adjust query based on preferred version
    if preferred_version == 'Live':
        query = f"{base_query} live"
    elif preferred_version == 'Acoustic':
        query = f"{base_query} acoustic"
    elif preferred_version == 'Remix':
        query = f"{base_query} remix"
    else:
        query = f"{base_query} official"

    try:
        request = youtube_client.search().list(
            q=query,
            part="snippet",
            type="video",
            maxResults=10
        )
        response = request.execute()

        best_matches = []
        for item in response['items']:
            video_title = item['snippet']['title']
            channel_title = item['snippet']['channelTitle']
            video_id = item['id']['videoId']
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            detected_version = detect_version_type(video_title)

            # Score based on version match and channel authority
            score = 0
            if detected_version == preferred_version:
                score += 10

            # Check for official channels
            if any(indicator in channel_title.lower() for indicator in
                   ['official', 'vevo', artist.lower().replace(' ', '')]):
                score += 5

            best_matches.append({
                'url': video_url,
                'title': video_title,
                'channel': channel_title,
                'version': detected_version,
                'score': score
            })

        # Sort by score and return best match
        best_matches.sort(key=lambda x: x['score'], reverse=True)
        return best_matches[0]['url'] if best_matches else None

    except Exception as e:
        logging.error(f"Error searching YouTube for '{artist} - {song_title}': {e}")
        return None


def search_spotify_with_version(artist, song_title, sp, preferred_version='Original'):
    """Enhanced Spotify search with version preference"""
    try:
        # Base search
        results = sp.search(q=f"track:{song_title} artist:{artist}", type="track", limit=20)

        if results and results['tracks']['items']:
            best_matches = []

            for track in results['tracks']['items']:
                track_artists = [a['name'].lower() for a in track['artists']]
                if artist.lower() in track_artists:
                    detected_version = detect_version_type(track['name'], track['album']['name'])

                    score = 0
                    if detected_version == preferred_version:
                        score += 10

                    # Prefer exact artist match
                    if track['artists'][0]['name'].lower() == artist.lower():
                        score += 5

                    best_matches.append({
                        'url': track['external_urls']['spotify'],
                        'name': track['name'],
                        'artist': track['artists'][0]['name'],
                        'version': detected_version,
                        'score': score
                    })

            # Sort by score and return best match
            best_matches.sort(key=lambda x: x['score'], reverse=True)
            return best_matches[0]['url'] if best_matches else None

        return None

    except Exception as e:
        logging.error(f"Error searching Spotify for '{artist} - {song_title}': {e}")
        return None


def batch_llm_process_songs(song_batch, llm_model):
    """Process multiple songs in a single LLM call for efficiency"""

    # Build batch input
    batch_input = ""
    for i, (row_num, artist, song_title) in enumerate(song_batch):
        batch_input += f"""
Row {row_num}:
Artist: "{artist}"
Song Text: "{song_title}"
"""

    prompt = f"""
אתה עוזר מוזיקה מומחה המתמחה במוזיקה ישראלית ועברית. נתח את המידע הבא על שירים וספק נתונים מדויקים בשפה המקורית (עברית לאמנים ישראליים, אנגלית לאמנים בינלאומיים).

**הוראות קריטיות:**
1. **עדיפות שפה:** אם זה אמן ישראלי או שיר עברי, השב בשמות ובכותרות עבריות. שמור על איות עברי מקורי ותווים.
2. **זיהוי שיר:** אם טקסט השיר נראה כמו מילים, זהה את כותרת השיר הרשמית בשפה המקורית.
3. **אימות אמן:** ספק את שם האמן הנכון בשפה המקורית (עברית לאמנים ישראליים).
4. **זיהוי סוג גרסה:** קבע סוג גרסה והשב באנגלית לשדה זה בלבד.

**נתוני קלט:**
{batch_input}

**פורמט פלט (מערך JSON בלבד, ללא טקסט נוסף):**
[
  {{
    "row": 123,
    "identified_song_title": "כותרת השיר הרשמית בשפה המקורית",
    "corrected_artist": "שם האמן הנכון בשפה המקורית", 
    "version_type": "Original/Live/Remix/Cover/Acoustic/Remastered/Other",
    "is_cover_version": true/false,
    "confidence": "high/medium/low",
    "explanation": "הסבר קצר באנגלית"
  }},
  {{
    "row": 124,
    "identified_song_title": "...",
    "corrected_artist": "...",
    "version_type": "...",
    "is_cover_version": false,
    "confidence": "...",
    "explanation": "..."
  }}
]

דוגמאות:
- אם הקלט הוא "Osher Cohen" → הפלט צריך להיות "אושר כהן"
- אם הקלט הוא "Eyal Golan" → הפלט צריך להיות "אייל גולן"
- אם הקלט הוא מילים בעברית → זהה כותרת שיר עברית
- אם הקלט הוא "Tuna" → הפלט צריך להיות "טונה"
- אם הקלט הוא "Chava Alberstein" → הפלט צריך להיות "חוה אלברשטיין"

השב עם מערך JSON בלבד, ללא טקסט או עיצוב נוסף.
"""

    try:
        response = llm_model.generate_content(prompt)
        llm_output_text = response.text.strip()

        # Clean up markdown code blocks and extra text
        if "```json" in llm_output_text:
            start = llm_output_text.find("```json") + 7
            end = llm_output_text.find("```", start)
            if end != -1:
                llm_output_text = llm_output_text[start:end]
        elif "```" in llm_output_text:
            start = llm_output_text.find("```") + 3
            end = llm_output_text.find("```", start)
            if end != -1:
                llm_output_text = llm_output_text[start:end]

        # Find JSON array in the response
        llm_output_text = llm_output_text.strip()
        if not llm_output_text.startswith('['):
            # Try to find the JSON array in the text
            start_bracket = llm_output_text.find('[')
            if start_bracket != -1:
                llm_output_text = llm_output_text[start_bracket:]

        # Parse JSON
        llm_data = json.loads(llm_output_text)

        # Convert to dictionary keyed by row number
        results = {}
        for item in llm_data:
            row_num = item.get('row')
            if row_num:
                results[row_num] = {
                    'corrected_artist': item.get('corrected_artist'),
                    'identified_song_title': item.get('identified_song_title'),
                    'version_type': item.get('version_type', 'Original'),
                    'confidence': item.get('confidence'),
                    'explanation': item.get('explanation')
                }

        return results

    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error in batch LLM processing: {e}")
        logging.error(f"Raw LLM response: {llm_output_text}")
        return {}
    except Exception as e:
        logging.error(f"Error in batch LLM processing: {e}")
        return {}


def pause_for_user_input(current_row, error_msg=""):
    """Pause processing and ask user whether to continue"""
    print(f"\n{'=' * 50}")
    print(f"PROCESSING PAUSED AT ROW {current_row}")
    if error_msg:
        print(f"ERROR: {error_msg}")
    print(f"{'=' * 50}")

    while True:
        choice = input(
            "\nChoose an option:\n1. Continue processing\n2. Stop and save progress\n3. Skip this row and continue\nEnter choice (1/2/3): ").strip()

        if choice == '1':
            return 'continue'
        elif choice == '2':
            return 'stop'
        elif choice == '3':
            return 'skip'
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")


def save_progress_state(current_row, log_filename):
    """Save current progress state"""
    state = {
        'last_processed_row': current_row,
        'timestamp': datetime.now().isoformat(),
        'log_file': log_filename
    }

    with open('processing_state.json', 'w') as f:
        json.dump(state, f, indent=2)

    logging.info(f"Progress saved. Last processed row: {current_row}")
    print(f"Progress saved to processing_state.json. Resume from row {current_row + 1} next time.")


def process_song_data():
    """Main processing function with enhanced logic"""
    # Setup logging
    log_filename = setup_logging()

    # Get user inputs
    spreadsheet_id, worksheet_name, start_row, end_row, batch_size = get_user_inputs()

    # Initialize APIs
    worksheet, youtube_service, sp, llm_model = initialize_apis(spreadsheet_id, worksheet_name)

    # Get data
    data = worksheet.get_all_values()
    headers = data[0]
    df = pd.DataFrame(data[1:], columns=headers)

    # Add Version Type column if it doesn't exist
    if 'Version Type' not in df.columns:
        df['Version Type'] = 'Original'

    # Add Notes column if it doesn't exist
    if 'Notes' not in df.columns:
        df['Notes'] = ''

    # Determine processing range
    total_rows = len(df)
    if end_row is None:
        end_row = total_rows + 1

    processing_range = range(start_row - 2, min(end_row - 1, total_rows))

    logging.info(
        f"Processing rows {start_row} to {min(end_row, total_rows + 1)} of worksheet '{worksheet_name}' in batches of {batch_size}")

    # Process in batches
    for batch_start in range(0, len(processing_range), batch_size):
        batch_end = min(batch_start + batch_size, len(processing_range))
        current_batch_indices = list(processing_range)[batch_start:batch_end]

        try:
            # Prepare batch for LLM processing
            llm_batch = []
            batch_data = []

            for index in current_batch_indices:
                row = df.iloc[index]
                actual_row_num = index + 2

                original_artist = row.get('Artist', '')
                original_song_title = row.get('Song Title', '')
                youtube_link = row.get('YouTube Link', '')
                spotify_link = row.get('Spotify Link', '')

                current_artist = original_artist
                current_song_title = original_song_title

                # Phase 1: Handle missing data from links
                if (not current_artist or not current_song_title) and (youtube_link or spotify_link):
                    if youtube_link:
                        yt_artist, yt_title, yt_version = get_youtube_metadata_from_url(youtube_link, youtube_service)
                        if yt_artist and yt_title:
                            current_artist = current_artist or yt_artist
                            current_song_title = current_song_title or yt_title

                    if spotify_link and (not current_artist or not current_song_title):
                        sp_artist, sp_title, sp_version = get_spotify_metadata_from_url(spotify_link, sp)
                        if sp_artist and sp_title:
                            current_artist = current_artist or sp_artist
                            current_song_title = current_song_title or sp_title

                # Add to batch for LLM processing
                if current_artist and current_song_title:
                    llm_batch.append((actual_row_num, current_artist, current_song_title))

                batch_data.append({
                    'index': index,
                    'row_num': actual_row_num,
                    'current_artist': current_artist,
                    'current_song_title': current_song_title,
                    'original_data': row
                })

            # Process batch with LLM
            logging.info(
                f"Processing LLM batch: rows {current_batch_indices[0] + 2} to {current_batch_indices[-1] + 2}")
            llm_results = batch_llm_process_songs(llm_batch, llm_model)

            # Process each row in the batch
            for row_data in batch_data:
                try:
                    index = row_data['index']
                    actual_row_num = row_data['row_num']
                    current_artist = row_data['current_artist']
                    current_song_title = row_data['current_song_title']
                    row = row_data['original_data']

                    youtube_link = row.get('YouTube Link', '')
                    spotify_link = row.get('Spotify Link', '')
                    version_type = row.get('Version Type', 'Original')
                    notes = row.get('Notes', '')

                    current_version_type = version_type

                    logging.info(
                        f"Processing row {actual_row_num}: Artist='{current_artist}', Song='{current_song_title}'")

                    # Apply LLM results if available
                    if actual_row_num in llm_results:
                        llm_result = llm_results[actual_row_num]
                        llm_artist = llm_result.get('corrected_artist')
                        llm_song = llm_result.get('identified_song_title')
                        llm_version = llm_result.get('version_type')
                        confidence = llm_result.get('confidence')

                        if confidence != "low" and llm_song and llm_artist:
                            if llm_song != current_song_title:
                                notes += " Song: fixed"
                                current_song_title = llm_song

                            if llm_artist != current_artist:
                                notes += " Artist: fixed"
                                current_artist = llm_artist

                            if llm_version and llm_version != current_version_type:
                                notes += f" Ver: {llm_version}"
                                current_version_type = llm_version
                        else:
                            notes += " LLM: uncertain"

                    # ALWAYS search for updated links if we have artist and song title
                    if current_artist and current_song_title:
                        logging.info(f"Searching for links: {current_artist} - {current_song_title}")

                        # Search YouTube
                        found_yt_link = search_youtube_with_version(
                            current_artist, current_song_title, youtube_service, current_version_type
                        )

                        # Search Spotify
                        found_sp_link = search_spotify_with_version(
                            current_artist, current_song_title, sp, current_version_type
                        )

                        # Update YouTube link
                        if found_yt_link:
                            if found_yt_link != youtube_link:
                                youtube_link = found_yt_link
                                notes += " YT: fixed"
                                logging.info(f"Updated YouTube link for row {actual_row_num}")
                            else:
                                logging.info(f"YouTube link already correct for row {actual_row_num}")
                        else:
                            if youtube_link:  # Had a link but couldn't find a better one
                                logging.info(f"No better YouTube link found for row {actual_row_num}")
                            else:
                                logging.warning(f"No YouTube link found for row {actual_row_num}")

                        # Update Spotify link
                        if found_sp_link:
                            if found_sp_link != spotify_link:
                                spotify_link = found_sp_link
                                notes += " Spotify: fixed"
                                logging.info(f"Updated Spotify link for row {actual_row_num}")
                            else:
                                logging.info(f"Spotify link already correct for row {actual_row_num}")
                        else:
                            if spotify_link:  # Had a link but couldn't find a better one
                                logging.info(f"No better Spotify link found for row {actual_row_num}")
                            else:
                                logging.warning(f"No Spotify link found for row {actual_row_num}")

                        # Add small delay between API calls
                        time.sleep(0.5)

                    # Update DataFrame
                    df.at[index, 'Artist'] = current_artist
                    df.at[index, 'Song Title'] = current_song_title
                    df.at[index, 'Version Type'] = current_version_type
                    df.at[index, 'YouTube Link'] = youtube_link
                    df.at[index, 'Spotify Link'] = spotify_link
                    df.at[index, 'Notes'] = notes

                except Exception as e:
                    error_msg = f"Error processing row {actual_row_num}: {e}"
                    logging.error(error_msg)

                    choice = pause_for_user_input(actual_row_num, error_msg)

                    if choice == 'stop':
                        save_progress_state(actual_row_num, log_filename)
                        return
                    elif choice == 'skip':
                        logging.info(f"Skipping row {actual_row_num}")
                        continue

            # Rate limiting between batches
            time.sleep(2)

        except Exception as e:
            error_msg = f"Error processing batch starting at row {current_batch_indices[0] + 2}: {e}"
            logging.error(error_msg)

            choice = pause_for_user_input(current_batch_indices[0] + 2, error_msg)

            if choice == 'stop':
                save_progress_state(current_batch_indices[0] + 2, log_filename)
                return
            elif choice == 'skip':
                logging.info(f"Skipping batch starting at row {current_batch_indices[0] + 2}")
                continue

    # Write updated data back to sheet
    try:
        worksheet.clear()
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        logging.info("Processing complete. Google Sheet updated successfully.")
        print("\n✅ Processing completed successfully!")

    except Exception as e:
        error_msg = f"Error updating Google Sheet: {e}"
        logging.error(error_msg)
        print(f"❌ {error_msg}")
        save_progress_state(len(processing_range), log_filename)


if __name__ == '__main__':
    try:
        process_song_data()
    except KeyboardInterrupt:
        print("\n\n⚠️  Processing interrupted by user")
        logging.info("Processing interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        logging.error(f"Unexpected error: {e}")
