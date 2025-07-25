import sys
import os
import time
import logging
import re
from datetime import datetime

# Set up simple logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# ========================================
# CONFIGURATION - UPDATE THESE VALUES!
# ========================================
# Google Sheets
CREDS_FILE = 'credentials.json'
# IMPORTANT: These are the correct scopes for Google Sheets
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive'
]

# Your API credentials
SPOTIFY_CLIENT_ID = '9d639f7edbc147f38864166ce4fe8b8b'
SPOTIFY_CLIENT_SECRET = '38aba7b1125642a1aa844ff8e24752d9'
YOUTUBE_API_KEY = 'AIzaSyBmr5g7WU7STMlywczX3sCE-P6uvNfoC6o'

# Output Column Indices (0-indexed)
# Column A = Artist (input) -> index 0
# Column B = Song Title (input) -> index 1
SPOTIFY_LINK_COL_IDX = 3  # Column D
YOUTUBE_LINK_COL_IDX = 4  # Column E
THUMBNAIL_COL_IDX = 8  # Column I
ALTERNATIVE_LINK_COL_IDX = 9  # Column J

YOUTUBE_QUOTA_LOG_FILE = 'youtube_quota_log.txt'

# Fuzzy matching thresholds (0-100)
# EXACT_MATCH_THRESHOLD for song is now the primary driver for "exact" match
EXACT_MATCH_THRESHOLD = 90  # For very close matches (e.g., minor punctuation differences, or strong song match)
HIGH_PROBABILITY_THRESHOLD = 75  # For good, but not perfect, matches (e.g., transliteration variations, extra words)


# ========================================

def check_packages():
    """Check if required packages are installed."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        import spotipy
        from spotipy.oauth2 import SpotifyClientCredentials
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        import unidecode
        from fuzzywuzzy import fuzz
        # Optional: check for python-Levenshtein for performance with fuzzywuzzy
        try:
            import Levenshtein
        except ImportError:
            logger.warning(
                "💡 For better performance with fuzzy matching, consider installing 'python-Levenshtein' (pip install python-Levenshtein).")
        return True
    except ImportError as e:
        logger.error(f"Missing package: {e}")
        logger.error(
            "Please ensure all required packages are installed (e.g., pip install gspread google-auth-oauthlib spotipy google-api-python-client unidecode fuzzywuzzy).")
        return False


if not check_packages():
    input("Press Enter to exit...")
    sys.exit(1)

# Import packages after checking
import gspread
from google.oauth2.service_account import Credentials
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import unidecode
from fuzzywuzzy import fuzz


def check_config():
    """Check if configuration is complete."""
    issues = []
    if not os.path.exists(CREDS_FILE):
        issues.append(f"❌ Missing: {CREDS_FILE}")
    if not SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_ID == 'YOUR_SPOTIFY_CLIENT_ID_HERE':
        issues.append("❌ Spotify Client ID not configured")
    if not SPOTIFY_CLIENT_SECRET or SPOTIFY_CLIENT_SECRET == 'YOUR_SPOTIFY_CLIENT_SECRET_HERE':
        issues.append("❌ Spotify Client Secret not configured")
    if not YOUTUBE_API_KEY or YOUTUBE_API_KEY == 'YOUR_YOUTUBE_API_KEY_HERE':
        issues.append("❌ YouTube API Key not configured")
    if issues:
        logger.error("⚠️  Configuration incomplete:")
        for issue in issues:
            logger.error(f"   {issue}")
        return False
    logger.info("✅ Configuration looks good!")
    return True


def get_google_client():
    """Get Google Sheets client after testing connection."""
    try:
        print("🔍 Testing Google Sheets connection...")
        creds = Credentials.from_service_account_file(CREDS_FILE, scopes=GOOGLE_SCOPES)
        print("✅ Credentials loaded successfully")
        client = gspread.authorize(creds)
        print("✅ Authorization successful")
        return client
    except FileNotFoundError:
        print(f"❌ Credentials file not found: {CREDS_FILE}")
        return None
    except Exception as e:
        print(f"❌ Google Sheets connection failed: {e}")
        return None


def normalize_artist_name(text):
    """Normalizes an artist name, including transliteration for non-Latin characters."""
    if not isinstance(text, str):
        return ""

    # Transliterate to ASCII approximation (e.g., Hebrew to Latin characters)
    text = unidecode.unidecode(text)

    # Convert to lowercase
    text = text.lower()
    # Remove common punctuation and special characters, but keep letters, numbers, and spaces
    text = re.sub(r'[^\w\s]', '', text, flags=re.UNICODE)
    # Replace multiple spaces with a single space and strip leading/trailing spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def normalize_song_title(text):
    """Normalizes a song title, preserving original script (e.g., Hebrew) but cleaning."""
    if not isinstance(text, str):
        return ""

    # Convert to lowercase
    text = text.lower()
    # Remove common punctuation and special characters, but keep letters, numbers, and spaces (Unicode aware)
    # This will preserve Hebrew characters.
    text = re.sub(r'[^\w\s]', '', text, flags=re.UNICODE)
    # Replace multiple spaces with a single space and strip leading/trailing spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def check_match(sheet_artist, sheet_song, link_artist, link_song):
    """
    Checks for a match between sheet data and link metadata using fuzzy matching.
    Prioritizes song title match.
    Returns "exact", "high_probability", or "none".
    """
    norm_sheet_artist = normalize_artist_name(sheet_artist)
    norm_sheet_song = normalize_song_title(sheet_song)
    norm_link_artist = normalize_artist_name(link_artist)
    norm_link_song = normalize_song_title(link_song)

    artist_score = fuzz.token_set_ratio(norm_sheet_artist, norm_link_artist)
    song_score = fuzz.token_set_ratio(norm_sheet_song, norm_link_song)

    logger.debug(
        f"   Match Scores: Artist='{sheet_artist}' vs '{link_artist}' -> {artist_score}, Song='{sheet_song}' vs '{link_song}' -> {song_score}")

    # New "Exact" Match Logic: If song title is a very strong match, consider it exact.
    # This fulfills "if there's a match in song name, but not necessarily the artist - add the link"
    if song_score >= EXACT_MATCH_THRESHOLD:
        return "exact"

    # High-probability match:
    # If both song and artist are reasonably close, but song isn't "exact"
    if song_score >= HIGH_PROBABILITY_THRESHOLD and artist_score >= HIGH_PROBABILITY_THRESHOLD:
        return "high_probability"

    return "none"


def search_spotify(sp, song, artist):
    """Search Spotify for a song and return link, artist, song, and thumbnail."""
    # Use the original (non-transliterated) song for search, but transliterated artist
    # Spotify's search is often good with mixed scripts or transliterations.
    search_queries = [
        f'track:"{song}" artist:"{artist}"',  # Most specific, original song, original artist
        f'track:"{normalize_song_title(song)}" artist:"{normalize_artist_name(artist)}"',
        # Normalized song, transliterated artist
        f'"{song}" "{artist}"',  # Exact phrases, original script
        f'{song} {artist}',  # Broad search, original script
        f'track:{song} artist:{artist}',  # Field-specific, no quotes for song/artist
        f'artist:"{artist}" {song}',  # Artist exact, song broad
        f'track:"{song}" {artist}'  # Song exact, artist broad
    ]

    for query in search_queries:
        try:
            results = sp.search(q=query, type='track', limit=1)
            if results['tracks']['items']:
                track = results['tracks']['items'][0]
                spotify_link = track['external_urls']['spotify']
                track_artist = track['artists'][0]['name']
                track_name = track['name']
                thumbnail_url = track['album']['images'][0]['url'] if track['album']['images'] else ""
                return spotify_link, track_artist, track_name, thumbnail_url
        except Exception as e:
            logger.error(f"   Spotify search error with query '{query}': {e}")
            # Continue to next query if there's an error with this one
    return None, None, None, None


def search_youtube(youtube, song, artist, row_num_in_sheet, youtube_quota_exceeded_flag):
    """Search YouTube for a song and return link, artist, song, and thumbnail."""
    if youtube_quota_exceeded_flag[0]:
        return None, None, None, None

    # Use original song and artist for search queries
    search_queries = [
        f"{song} {artist} official audio",
        f"{song} {artist} official video",
        f"{song} {artist} lyric video",
        f"{song} {artist}"  # Broadest search
    ]

    for query in search_queries:
        try:
            request = youtube.search().list(
                q=query,
                part='snippet',
                maxResults=1,
                type='video'
            )
            response = request.execute()
            if response['items']:
                video_item = response['items'][0]
                video_id = video_item['id']['videoId']
                youtube_link = f'https://www.youtube.com/watch?v={video_id}'

                video_title = video_item['snippet']['title']
                channel_title = video_item['snippet']['channelTitle']

                # Heuristic for parsing artist/song from video title
                # Prioritize parsing from title if possible, otherwise use channel/full title
                parsed_artist = channel_title
                parsed_song = video_title

                if ' - ' in video_title:
                    parts = video_title.split(' - ', 1)
                    parsed_artist = parts[0].strip()
                    parsed_song = parts[1].strip()
                elif ' by ' in video_title:
                    parts = video_title.split(' by ', 1)
                    parsed_song = parts[0].strip()
                    parsed_artist = parts[1].strip()

                # If the parsed artist/song are very short or generic, fall back to broader parts
                if len(parsed_artist) < 3 and channel_title:
                    parsed_artist = channel_title
                if len(parsed_song) < 3 and video_title:
                    parsed_song = video_title

                thumbnail_url = video_item['snippet']['thumbnails']['high']['url'] if 'high' in video_item['snippet'][
                    'thumbnails'] else ""

                return youtube_link, parsed_artist, parsed_song, thumbnail_url
        except HttpError as e:
            if e.resp.status == 403 and "quotaExceeded" in str(e):
                logger.error(
                    f"   ❌ YouTube API Quota Exceeded at row {row_num_in_sheet}. Logging and stopping further YouTube requests.")
                with open(YOUTUBE_QUOTA_LOG_FILE, 'w') as f:
                    f.write(f"{row_num_in_sheet}\n")
                youtube_quota_exceeded_flag[0] = True
                return None, None, None, None  # Stop immediately on quota error
            else:
                logger.error(f"   YouTube API error (HTTP {e.resp.status}) with query '{query}': {e}")
        except Exception as e:
            logger.error(f"   YouTube search error with query '{query}': {e}")

    return None, None, None, None


def process_worksheet(sheet, worksheet, sp, youtube, link_source, row_range, youtube_quota_exceeded_flag,
                      resume_row=None):
    """Processes a single worksheet to find and update music links."""
    print(f"\n📋 Reading worksheet: '{worksheet.title}'...")
    all_values = worksheet.get_all_values()
    if len(all_values) < 2:
        print(f"❌ No data found in worksheet '{worksheet.title}' (need at least 2 rows including header)")
        return

    # Ensure the sheet has enough columns for output
    # We need at least J column, which is index 9.
    # If the sheet has fewer columns, we'll extend the rows with empty strings.
    min_cols_needed = max(SPOTIFY_LINK_COL_IDX, YOUTUBE_LINK_COL_IDX, THUMBNAIL_COL_IDX, ALTERNATIVE_LINK_COL_IDX) + 1

    print(f"📊 Found {len(all_values)} rows in worksheet '{worksheet.title}'")

    # Determine row processing range
    start_row_idx = 1  # Skip header (row 1 is index 0)
    end_row_idx = len(all_values) - 1  # Last row index

    if resume_row and resume_row > start_row_idx + 1:  # resume_row is 1-indexed
        print(f"Resuming from row {resume_row} as requested.")
        start_row_idx = resume_row - 1

    if row_range.lower() != 'all':
        try:
            if '-' in row_range:
                start_str, end_str = row_range.split('-')
                temp_start_idx = int(start_str) - 1  # Convert to 0-indexed
                if end_str.lower() == 'end':
                    pass  # end_row_idx remains len(all_values) - 1
                else:
                    end_row_idx = int(end_str) - 1  # Convert to 0-indexed

                # Use the later start_row_idx if resuming
                start_row_idx = max(start_row_idx, temp_start_idx)

            else:
                # Single row specified
                temp_start_idx = int(row_range) - 1
                end_row_idx = temp_start_idx
                # Use the later start_row_idx if resuming
                start_row_idx = max(start_row_idx, temp_start_idx)

            if start_row_idx < 1 or start_row_idx > end_row_idx or end_row_idx >= len(all_values):
                print(
                    f"⚠️ Invalid row range '{row_range}' for worksheet '{worksheet.title}'. Processing all rows from current start.")
                start_row_idx = max(1, start_row_idx)  # Ensure not less than 1
                end_row_idx = len(all_values) - 1
        except ValueError:
            print(
                f"⚠️ Invalid row range format '{row_range}' for worksheet '{worksheet.title}'. Processing all rows from current start.")
            start_row_idx = max(1, start_row_idx)  # Ensure not less than 1
            end_row_idx = len(all_values) - 1

    print(f"🔄 Processing rows from {start_row_idx + 1} to {end_row_idx + 1} in '{worksheet.title}'")

    # Ask user to confirm column mapping
    print("\n🔍 Please confirm your column structure for this worksheet:")
    print("   Column A = Artist (Input)")
    print("   Column B = Song Title (Input)")
    print(f"   Column {chr(65 + SPOTIFY_LINK_COL_IDX)} = Spotify Links (Output)")
    print(f"   Column {chr(65 + YOUTUBE_LINK_COL_IDX)} = YouTube Links (Output)")
    print(f"   Column {chr(65 + THUMBNAIL_COL_IDX)} = Thumbnail URL (Output)")
    print(f"   Column {chr(65 + ALTERNATIVE_LINK_COL_IDX)} = Alternative Link (Output)")
    confirm = input("\nIs this correct? (y/n): ").lower().strip()
    if confirm != 'y' and confirm != 'yes':
        print("Skipping this worksheet. Please update the column mapping in the script and try again for others.")
        return

    # Process each row with CORRECTED column mapping
    updates = []
    processed_count = 0

    # Iterate from the determined start_row_idx to end_row_idx (inclusive)
    for i in range(start_row_idx, end_row_idx + 1):
        row_num_in_sheet = i + 1  # Convert 0-indexed to 1-indexed sheet row number
        row = all_values[i]

        # Pad row with empty strings if it doesn't have enough columns for output
        if len(row) < min_cols_needed:
            row.extend([''] * (min_cols_needed - len(row)))

        if len(row) >= 2:  # Need at least columns A and B
            artist = row[0].strip() if len(row) > 0 else ""  # Column A = Artist
            song = row[1].strip() if len(row) > 1 else ""  # Column B = Song Title

            if song and artist:
                processed_count += 1
                print(f"\n🎼 ({processed_count}) Processing Row {row_num_in_sheet}: '{song}' by '{artist}'")

                # Check if links already exist in the new columns
                spotify_link_exists = row[SPOTIFY_LINK_COL_IDX] and row[SPOTIFY_LINK_COL_IDX] != "Not Found"
                youtube_link_exists = row[YOUTUBE_LINK_COL_IDX] and row[YOUTUBE_LINK_COL_IDX] != "Not Found"
                thumbnail_exists = row[THUMBNAIL_COL_IDX] and row[THUMBNAIL_COL_IDX] != "Not Found"
                alternative_link_exists = row[ALTERNATIVE_LINK_COL_IDX] and row[ALTERNATIVE_LINK_COL_IDX] != "Not Found"

                # Initialize values for this row's update
                current_spotify_link = row[SPOTIFY_LINK_COL_IDX]
                current_youtube_link = row[YOUTUBE_LINK_COL_IDX]
                current_thumbnail_link = row[THUMBNAIL_COL_IDX]
                current_alternative_link = row[ALTERNATIVE_LINK_COL_IDX]

                # Get Spotify link if requested and not already present
                if link_source in ['spotify', 'both']:
                    if not spotify_link_exists:
                        print("   🔍 Searching Spotify...")
                        spotify_link, sp_artist, sp_song, sp_thumbnail = search_spotify(sp, song, artist)

                        if spotify_link:
                            match_type = check_match(artist, song, sp_artist, sp_song)
                            if match_type == "exact":
                                current_spotify_link = spotify_link
                                current_thumbnail_link = sp_thumbnail
                                print(f"   🎵 Spotify (Exact Match): {spotify_link}")
                            elif match_type == "high_probability":
                                current_alternative_link = spotify_link  # Store as alternative
                                print(f"   🎵 Spotify (High Probability Match - Alternative): {spotify_link}")
                            else:
                                print("   🎵 Spotify: No definitive match found.")
                        else:
                            print("   🎵 Spotify: Not Found.")
                        time.sleep(0.5)
                    else:
                        print("   ✅ Spotify link already exists")
                else:
                    print("   ⏩ Spotify search skipped (not requested)")

                # Get YouTube link if requested and not already present
                if link_source in ['youtube', 'both'] and not youtube_quota_exceeded_flag[0]:
                    if not youtube_link_exists:
                        print("   🔍 Searching YouTube...")
                        yt_link, yt_artist, yt_song, yt_thumbnail = search_youtube(youtube, song, artist,
                                                                                   row_num_in_sheet,
                                                                                   youtube_quota_exceeded_flag)

                        if yt_link and yt_link != "QUOTA_EXCEEDED":
                            match_type = check_match(artist, song, yt_artist, yt_song)
                            if match_type == "exact":
                                current_youtube_link = yt_link
                                # Only update thumbnail if Spotify didn't provide one or if YouTube's is preferred
                                if not current_thumbnail_link:
                                    current_thumbnail_link = yt_thumbnail
                                print(f"   📺 YouTube (Exact Match): {yt_link}")
                            elif match_type == "high_probability":
                                # Only add to alternative if not already set by Spotify
                                if not current_alternative_link:
                                    current_alternative_link = yt_link
                                print(f"   📺 YouTube (High Probability Match - Alternative): {yt_link}")
                            else:
                                print("   📺 YouTube: No definitive match found.")
                        elif yt_link == "QUOTA_EXCEEDED":
                            print("   ⚠️  YouTube search stopped due to quota.")
                        else:
                            print("   📺 YouTube: Not Found.")
                        time.sleep(0.5)
                    else:
                        print("   ✅ YouTube link already exists")
                elif youtube_quota_exceeded_flag[0]:
                    print("   ⏩ YouTube search skipped (quota exceeded in previous row).")
                else:
                    print("   ⏩ YouTube search skipped (not requested)")

                # Prepare updates for this row
                # Ensure the row is long enough to accommodate all new columns
                new_row_values = row[:]  # Make a copy

                # Extend the row if necessary to reach the highest column index
                max_idx = max(SPOTIFY_LINK_COL_IDX, YOUTUBE_LINK_COL_IDX, THUMBNAIL_COL_IDX, ALTERNATIVE_LINK_COL_IDX)
                if len(new_row_values) <= max_idx:
                    new_row_values.extend([''] * (max_idx + 1 - new_row_values))

                # Update the specific cells
                new_row_values[SPOTIFY_LINK_COL_IDX] = current_spotify_link
                new_row_values[YOUTUBE_LINK_COL_IDX] = current_youtube_link
                new_row_values[THUMBNAIL_COL_IDX] = current_thumbnail_link
                new_row_values[ALTERNATIVE_LINK_COL_IDX] = current_alternative_link

                # Add to batch update if any of the target cells have changed
                # This check prevents unnecessary updates if the values are already correct
                if (row[SPOTIFY_LINK_COL_IDX] != current_spotify_link or
                        row[YOUTUBE_LINK_COL_IDX] != current_youtube_link or
                        row[THUMBNAIL_COL_IDX] != current_thumbnail_link or
                        row[ALTERNATIVE_LINK_COL_IDX] != current_alternative_link):
                    # Only update the specific cells, not the whole row, for efficiency
                    updates.append({'range': f'{chr(65 + SPOTIFY_LINK_COL_IDX)}{row_num_in_sheet}',
                                    'values': [[current_spotify_link]]})
                    updates.append({'range': f'{chr(65 + YOUTUBE_LINK_COL_IDX)}{row_num_in_sheet}',
                                    'values': [[current_youtube_link]]})
                    updates.append({'range': f'{chr(65 + THUMBNAIL_COL_IDX)}{row_num_in_sheet}',
                                    'values': [[current_thumbnail_link]]})
                    updates.append({'range': f'{chr(65 + ALTERNATIVE_LINK_COL_IDX)}{row_num_in_sheet}',
                                    'values': [[current_alternative_link]]})
            else:
                print(f"   ⚠️  Row {row_num_in_sheet}: Missing song or artist data. Skipping.")
        else:
            print(f"   ⚠️  Row {row_num_in_sheet}: Not enough columns (expected at least 2). Skipping.")

    # Apply all updates
    if updates:
        print(f"\n📝 Updating {len(updates)} cells in worksheet '{worksheet.title}'...")
        worksheet.batch_update(updates)
        print("✅ All updates completed for this worksheet!")
    else:
        print(
            f"\nℹ️  No updates needed for worksheet '{worksheet.title}' - all songs already have requested links or no valid rows found.")
    print(f"\n🎉 Finished processing worksheet '{worksheet.title}'. Processed {processed_count} valid song entries.")


def main():
    """Main function."""
    print("🎵 Music Link Automation (Enhanced Version)")
    print("=" * 60)

    # Check configuration
    if not check_config():
        input("\nPress Enter to exit...")
        return

    youtube_quota_exceeded_flag = [False]  # Use a mutable list to pass by reference

    # Check for previous YouTube quota exceedance
    resume_row = None
    if os.path.exists(YOUTUBE_QUOTA_LOG_FILE):
        with open(YOUTUBE_QUOTA_LOG_FILE, 'r') as f:
            last_logged_row = f.readline().strip()
        if last_logged_row.isdigit():
            resume_row = int(last_logged_row)
            print(f"\n⚠️  Previous YouTube API quota exceeded at row {resume_row}.")
            choice = input(
                f"Do you want to resume processing from row {resume_row}? (y/n, default 'y'): ").lower().strip()
            if choice == 'n':
                resume_row = None
                os.remove(YOUTUBE_QUOTA_LOG_FILE)  # Clear log if not resuming
                print("Starting from the beginning.")
            else:
                print(f"Resuming from row {resume_row}.")
        else:
            os.remove(YOUTUBE_QUOTA_LOG_FILE)  # Clear invalid log file
            print("Invalid YouTube quota log file found. Starting from the beginning.")

    try:
        # Get Google Sheets client
        client = get_google_client()
        if not client:
            input("\nPress Enter to exit...")
            return

        # --- A: Ask for link source ---
        link_source = ""
        while link_source not in ['spotify', 'youtube', 'both']:
            link_source = input("Retrieve links from (spotify/youtube/both)? ").lower().strip()
            if link_source not in ['spotify', 'youtube', 'both']:
                print("Invalid input. Please type 'spotify', 'youtube', or 'both'.")
        print(f"Selected link source: {link_source.capitalize()}")

        # --- C: Ask for worksheets ---
        spreadsheet_name = input("Enter the name of your Google Sheet (e.g., 'songs'): ").strip()
        try:
            spreadsheet = client.open(spreadsheet_name)
            print(f"✅ Google Sheet '{spreadsheet_name}' opened successfully.")
        except gspread.SpreadsheetNotFound:
            print(f"❌ Google Sheet '{spreadsheet_name}' not found.")
            input("Press Enter to exit...")
            return

        available_worksheets = [ws.title for ws in spreadsheet.worksheets()]
        print(f"\nAvailable worksheets in '{spreadsheet_name}': {', '.join(available_worksheets)}")
        worksheet_choice = input("Enter worksheet name(s) (comma-separated, or 'all'): ").lower().strip()
        worksheets_to_process = []
        if worksheet_choice == 'all':
            worksheets_to_process = spreadsheet.worksheets()
        else:
            chosen_names = [name.strip() for name in worksheet_choice.split(',')]
            for name in chosen_names:
                try:
                    ws = spreadsheet.worksheet(name)
                    worksheets_to_process.append(ws)
                except gspread.WorksheetNotFound:
                    print(f"⚠️ Worksheet '{name}' not found. Skipping.")

        if not worksheets_to_process:
            print("No valid worksheets selected or found. Exiting.")
            input("Press Enter to exit...")
            return

        # --- B: Ask for row range ---
        row_range = input("Enter row range to process (e.g., '2-10', '2-end', or 'all'): ").lower().strip()
        if not row_range:
            row_range = 'all'  # Default to all if empty input

        print("\n🎧 Connecting to Spotify...")
        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET
        ))
        print("✅ Spotify connected")

        print("📺 Connecting to YouTube...")
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        print("✅ YouTube connected")

        for ws in worksheets_to_process:
            process_worksheet(spreadsheet, ws, sp, youtube, link_source, row_range, youtube_quota_exceeded_flag,
                              resume_row)
            # If quota was hit, stop processing further worksheets for YouTube
            if youtube_quota_exceeded_flag[0]:
                print("\nStopping further YouTube searches across worksheets due to quota exceedance.")
                break  # Exit the loop over worksheets

        print(f"\n🎉 All selected worksheets processed in '{spreadsheet_name}'!")
        # If the script completes successfully, clear the quota log
        if os.path.exists(YOUTUBE_QUOTA_LOG_FILE) and not youtube_quota_exceeded_flag[0]:
            os.remove(YOUTUBE_QUOTA_LOG_FILE)
            print("YouTube quota log cleared as processing completed successfully.")

    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
        print("Please check your configuration and try again.")
        logger.exception("An unexpected error occurred in main:")  # Log full traceback

    input("\nPress Enter to exit...")


if __name__ == '__main__':
    main()
