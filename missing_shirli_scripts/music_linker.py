"""
Fixed Music Link Automation Script - Corrected column mapping
Column A = Artist, Column B = Song Title
"""

import sys
import os
import time
import logging

# Set up simple logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# ========================================
# CONFIGURATION - UPDATE THESE VALUES!
# ========================================

# Google Sheets
CREDS_FILE = 'credentials.json'
# SHEET_NAME is now dynamic based on user input
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

# ========================================

def check_packages():
    """Check if required packages are installed."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        import spotipy
        from spotipy.oauth2 import SpotifyClientCredentials
        from googleapiclient.discovery import build
        return True
    except ImportError as e:
        logger.error(f"Missing package: {e}")
        logger.error("Please run setup_windows.bat first!")
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

def search_spotify(sp, song, artist):
    """Search Spotify for a song."""
    try:
        # Try exact search first
        query = f'track:"{song}" artist:"{artist}"'
        results = sp.search(q=query, type='track', limit=1)

        if results['tracks']['items']:
            return results['tracks']['items'][0]['external_urls']['spotify']

        # Try broader search
        query = f"{song} {artist}"
        results = sp.search(q=query, type='track', limit=1)

        if results['tracks']['items']:
            return results['tracks']['items'][0]['external_urls']['spotify']

    except Exception as e:
        logger.error(f"   Spotify error: {e}")

    return "Not Found"

def search_youtube(youtube, song, artist):
    """Search YouTube for a song."""
    try:
        query = f"{song} {artist} official"

        request = youtube.search().list(
            q=query,
            part='snippet',
            maxResults=1,
            type='video'
        )
        response = request.execute()

        if response['items']:
            video_id = response['items'][0]['id']['videoId']
            return f'https://www.youtube.com/watch?v={video_id}'

    except Exception as e:
        logger.error(f"   YouTube error: {e}")

    return "Not Found"

def process_worksheet(sheet, worksheet, sp, youtube, link_source, row_range):
    """Processes a single worksheet to find and update music links."""
    print(f"\n📋 Reading worksheet: '{worksheet.title}'...")

    all_values = worksheet.get_all_values()

    if len(all_values) < 2:
        print(f"❌ No data found in worksheet '{worksheet.title}' (need at least 2 rows including header)")
        return

    print(f"📊 Found {len(all_values)} rows in worksheet '{worksheet.title}'")

    # Determine row processing range
    start_row_idx = 1 # Skip header (row 1 is index 0)
    end_row_idx = len(all_values) - 1 # Last row index

    if row_range.lower() != 'all':
        try:
            if '-' in row_range:
                start_str, end_str = row_range.split('-')
                start_row_idx = int(start_str) - 1 # Convert to 0-indexed
                if end_str.lower() == 'end':
                    pass # end_row_idx remains len(all_values) - 1
                else:
                    end_row_idx = int(end_str) - 1 # Convert to 0-indexed
            else:
                # Single row specified
                start_row_idx = int(row_range) - 1
                end_row_idx = start_row_idx

            if start_row_idx < 1 or start_row_idx > end_row_idx or end_row_idx >= len(all_values):
                print(f"⚠️ Invalid row range '{row_range}' for worksheet '{worksheet.title}'. Processing all rows.")
                start_row_idx = 1
                end_row_idx = len(all_values) - 1
        except ValueError:
            print(f"⚠️ Invalid row range format '{row_range}' for worksheet '{worksheet.title}'. Processing all rows.")
            start_row_idx = 1
            end_row_idx = len(all_values) - 1

    print(f"🔄 Processing rows from {start_row_idx + 1} to {end_row_idx + 1} in '{worksheet.title}'")

    # Ask user to confirm column mapping
    print("\n🔍 Please confirm your column structure for this worksheet:")
    print("   Column A = Artist")
    print("   Column B = Song Title")
    print("   Column F = Spotify Links (will be added)")
    print("   Column G = YouTube Links (will be added)")

    confirm = input("\nIs this correct? (y/n): ").lower().strip()
    if confirm != 'y' and confirm != 'yes':
        print("Skipping this worksheet. Please update the column mapping in the script and try again for others.")
        return

    # Process each row with CORRECTED column mapping
    updates = []
    processed_count = 0

    # Iterate from the determined start_row_idx to end_row_idx (inclusive)
    for i in range(start_row_idx, end_row_idx + 1):
        row_num_in_sheet = i + 1 # Convert 0-indexed to 1-indexed sheet row number
        row = all_values[i]

        if len(row) >= 2:  # Need at least columns A and B
            # CORRECTED: Column A = Artist, Column B = Song
            artist = row[0].strip() if len(row) > 0 else ""    # Column A = Artist
            song = row[1].strip() if len(row) > 1 else ""     # Column B = Song Title

            if song and artist:
                processed_count += 1
                print(f"\n🎼 ({processed_count}) Processing Row {row_num_in_sheet}: '{song}' by '{artist}'")

                # Check if links already exist (ensure row is long enough before accessing indices)
                spotify_exists = len(row) > 5 and row[5] and row[5] != "Not Found"
                youtube_exists = len(row) > 6 and row[6] and row[6] != "Not Found"

                # Get Spotify link if requested
                if link_source in ['spotify', 'both']:
                    if not spotify_exists:
                        print("   🔍 Searching Spotify...")
                        spotify_link = search_spotify(sp, song, artist)
                        updates.append({'range': f'F{row_num_in_sheet}', 'values': [[spotify_link]]})
                        print(f"   🎵 Spotify: {spotify_link}")
                        time.sleep(0.5)
                    else:
                        print("   ✅ Spotify link already exists")
                else:
                    print("   ⏩ Spotify search skipped (not requested)")


                # Get YouTube link if requested
                if link_source in ['youtube', 'both']:
                    if not youtube_exists:
                        print("   🔍 Searching YouTube...")
                        youtube_link = search_youtube(youtube, song, artist)
                        updates.append({'range': f'G{row_num_in_sheet}', 'values': [[youtube_link]]})
                        print(f"   📺 YouTube: {youtube_link}")
                        time.sleep(0.5)
                    else:
                        print("   ✅ YouTube link already exists")
                else:
                    print("   ⏩ YouTube search skipped (not requested)")

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
        print(f"\nℹ️  No updates needed for worksheet '{worksheet.title}' - all songs already have requested links or no valid rows found.")

    print(f"\n🎉 Finished processing worksheet '{worksheet.title}'. Processed {processed_count} valid song entries.")


def main():
    """Main function."""
    print("🎵 Music Link Automation (Enhanced Version)")
    print("=" * 60)

    # Check configuration
    if not check_config():
        input("\nPress Enter to exit...")
        return

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
            row_range = 'all' # Default to all if empty input

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
            process_worksheet(spreadsheet, ws, sp, youtube, link_source, row_range)

        print(f"\n🎉 All selected worksheets processed in '{spreadsheet_name}'!")

    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
        print("Please check your configuration and try again.")

    input("\nPress Enter to exit...")

if __name__ == '__main__':
    main()
