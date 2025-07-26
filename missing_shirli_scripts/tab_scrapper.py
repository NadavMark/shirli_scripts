import requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials
import time
import random
import urllib.parse
import logging
from typing import Optional, Tuple
import json
import re # Import re for regex operations
import sys # Import sys to configure stdout encoding

# Configure logging
# Set up a logger instance
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Clear existing handlers to prevent duplicate logs if run multiple times
if logger.handlers:
    for handler in logger.handlers:
        logger.removeHandler(handler)

# Create a file handler with UTF-8 encoding
file_handler = logging.FileHandler('scraper.log', encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Create a stream handler (for console output) with UTF-8 encoding
# Ensure sys.stdout encoding is set to utf-8 for the console output
# This is crucial for Windows environments where default might be cp1252
if sys.stdout.encoding != 'utf-8':
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(stream_handler)


class Tab4UScraper:
    def __init__(self, credentials_file: str):
        """
        Initialize the scraper with Google Sheets credentials.

        Args:
            credentials_file: Path to Google service account JSON file
        """
        self.credentials_file = credentials_file
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
        })

        # Sleep configuration (8-20 seconds as recommended)
        self.min_sleep = 8
        self.max_sleep = 20

        # Initialize Google Sheets client (without specific sheet/worksheet yet)
        self.gc = None
        self._setup_google_sheets_client()

    def _setup_google_sheets_client(self):
        """Setup Google Sheets API connection client."""
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]

            creds = Credentials.from_service_account_file(
                self.credentials_file,
                scopes=scope
            )

            self.gc = gspread.authorize(creds)
            logger.info("Successfully connected to Google Sheets API client.")

        except Exception as e:
            logger.error(f"Failed to setup Google Sheets connection: {e}")
            raise

    def _polite_sleep(self):
        """Implement polite delay between requests."""
        sleep_time = random.uniform(self.min_sleep, self.max_sleep)
        logger.info(f"Sleeping for {sleep_time:.2f} seconds...")
        time.sleep(sleep_time)

    def _construct_search_url(self, artist: str, song: str) -> str:
        """
        Construct the search URL for tab4u.com with proper Hebrew text handling.

        Args:
            artist: Artist name (Hebrew or English)
            song: Song title (Hebrew or English)

        Returns:
            Formatted search URL
        """
        query = f"{artist} {song}".strip()

        # Ensure proper encoding for Hebrew text
        try:
            encoded_query = urllib.parse.quote(query, safe='')
            search_url = f"https://www.tab4u.com/resultsSimple?tab=songs&q={encoded_query}"
            logger.debug(f"Constructed URL for '{query}': {search_url}")
            return search_url
        except Exception as e:
            logger.error(f"Error encoding query '{query}': {e}")
            # Fallback: try with UTF-8 encoding
            try:
                encoded_query = urllib.parse.quote(query.encode('utf-8'), safe='')
                return f"https://www.tab4u.com/resultsSimple?tab=songs&q={encoded_query}"
            except:
                logger.error(f"Failed to encode query: {query}")
                return f"https://www.tab4u.com/resultsSimple?tab=songs&q="

    def _extract_chord_url(self, html_content: str, artist: str, song: str) -> Optional[str]:
        """
        Extract the direct chord page URL from search results HTML.
        Enhanced for Hebrew text handling and refined matching logic.
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Look for song result rows in the table
            song_rows = soup.find_all('tr')

            results_found = []

            for row in song_rows:
                # Find the song cell (td with class songTd1)
                song_cell = row.find('td', class_='songTd1')
                if not song_cell:
                    continue

                # Find the song link (a with class ruSongLink)
                song_link = song_cell.find('a', class_='ruSongLink')
                if not song_link:
                    continue

                href = song_link.get('href', '')
                if not href or not href.startswith('tabs/songs/'):
                    continue

                # Get the song and artist info from the link
                song_name_div = song_link.find('div', class_='sNameI19')
                artist_name_div = song_link.find('div', class_='aNameI19')

                if song_name_div and artist_name_div:
                    found_song = song_name_div.get_text(strip=True).replace(' /', '').strip()
                    found_artist = artist_name_div.get_text(strip=True).strip()

                    full_url = f"https://www.tab4u.com/{href}"

                    results_found.append({
                        'url': full_url,
                        'song': found_song,
                        'artist': found_artist,
                        'href': href
                    })

                    logger.debug(f"Found result: {found_artist} - {found_song} -> {full_url}")

            if not results_found:
                logger.warning(f"No chord results found for {artist} - {song}")
                return None

            # --- Refined Matching Logic ---
            # 1. Try to find an exact match (both artist and song)
            for result in results_found:
                artist_match = (
                        artist.lower() in result['artist'].lower() or
                        result['artist'].lower() in artist.lower() or
                        self._similar_text(artist, result['artist'])
                )
                song_match = (
                        song.lower() in result['song'].lower() or
                        result['song'].lower() in song.lower() or
                        self._similar_text(song, result['song'])
                )
                if artist_match and song_match:
                    logger.info(f"Found exact match (artist + song) for {artist} - {song}: {result['url']}")
                    return result['url']

            # 2. If no exact match, try to find a song-only match
            for result in results_found:
                song_match = (
                        song.lower() in result['song'].lower() or
                        result['song'].lower() in song.lower() or
                        self._similar_text(song, result['song'])
                )
                if song_match:
                    logger.info(f"Found song-only match for '{song}' (original artist '{artist}'): {result['url']}")
                    return result['url']

            # 3. If neither exact nor song-only match, return None (leave empty)
            logger.info(f"No exact or song-only match found for {artist} - {song}. Leaving URL empty.")
            return None

        except Exception as e:
            logger.error(f"Error extracting chord URL for {artist} - {song}: {e}")
            return None

    def _similar_text(self, text1: str, text2: str) -> bool:
        """
        Check if two texts are similar (for Hebrew text matching).
        """
        # Remove common punctuation and normalize
        def normalize(text):
            # Remove punctuation and extra spaces
            text = re.sub(r'[^\w\s]', '', text)
            text = re.sub(r'\s+', ' ', text)
            return text.strip().lower()

        norm1 = normalize(text1)
        norm2 = normalize(text2)

        # Check if one contains the other (at least 70% overlap)
        if len(norm1) > 0 and len(norm2) > 0:
            shorter = norm1 if len(norm1) < len(norm2) else norm2
            longer = norm2 if len(norm1) < len(norm2) else norm1

            # Simple substring check for similarity
            if len(shorter) >= 3:  # Only for meaningful text
                return shorter in longer

        return False

    def _search_tab4u(self, artist: str, song: str) -> Optional[str]:
        """
        Search for a song on tab4u.com and return the direct chord URL.

        Args:
            artist: Artist name
            song: Song title

        Returns:
            Direct chord URL or None if not found
        """
        search_url = self._construct_search_url(artist, song)
        logger.info(f"Searching tab4u.com for: {artist} - {song}")
        logger.info(f"Search URL: {search_url}")

        try:
            response = self.session.get(search_url, timeout=30)
            response.raise_for_status()

            chord_url = self._extract_chord_url(response.text, artist, song)
            return chord_url

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {artist} - {song}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error searching for {artist} - {song}: {e}")
            return None


    def process_worksheet(self, worksheet: gspread.Worksheet, start_row: int, end_row: int):
        """
        Process specified rows in a given Google Sheet worksheet and update with chord URLs.

        Args:
            worksheet: The gspread Worksheet object to process.
            start_row: The 1-indexed starting row number to process.
            end_row: The 1-indexed ending row number to process.
        """
        try:
            logger.info(f"\n--- Processing worksheet: '{worksheet.title}' (Rows {start_row}-{end_row}) ---")

            # Get column headers to identify artist and song columns
            headers = worksheet.row_values(1)
            logger.info(f"Available columns in '{worksheet.title}': {headers}")

            # Try to identify artist and song columns (flexible mapping)
            artist_col_idx = None
            song_col_idx = None

            # Look for common column names (English and Hebrew)
            for i, header in enumerate(headers):
                header_lower = header.lower().strip()
                # English variations
                if header_lower in ['artist', 'artists', 'performer', 'singer']:
                    artist_col_idx = i
                elif header_lower in ['song', 'title', 'song title', 'track']:
                    song_col_idx = i
                # Hebrew variations (add common Hebrew terms)
                elif 'אמן' in header or 'זמר' in header or 'ביצוע' in header:
                    artist_col_idx = i
                elif 'שיר' in header or 'כותרת' in header or 'שם השיר' in header:
                    song_col_idx = i

            # If not found by name, assume columns A and B
            if artist_col_idx is None:
                artist_col_idx = 0  # Column A
                logger.warning("Artist column not identified by header, assuming Column A")
            if song_col_idx is None:
                song_col_idx = 1  # Column B
                logger.warning("Song column not identified by header, assuming Column B")

            logger.info(
                f"Using Artist column: {artist_col_idx + 1} ({headers[artist_col_idx] if artist_col_idx < len(headers) else 'N/A'})")
            logger.info(
                f"Using Song column: {song_col_idx + 1} ({headers[song_col_idx] if song_col_idx < len(headers) else 'N/A'})")

            # Get all data from the worksheet
            all_data = worksheet.get_all_values()
            total_rows_in_sheet = len(all_data)

            # Adjust end_row if it's 'end' or exceeds actual data
            actual_end_row = min(end_row, total_rows_in_sheet)

            if start_row > actual_end_row:
                logger.warning(f"Start row ({start_row}) is beyond end row ({actual_end_row}). No rows to process.")
                return

            logger.info(f"Processing data rows from {start_row} to {actual_end_row} (inclusive)")

            processed_count = 0
            found_count = 0
            updates_batch = [] # To store updates for batch processing

            # Iterate from the specified start_row to actual_end_row (1-indexed)
            for row_num_1_indexed in range(start_row, actual_end_row + 1):
                # Convert to 0-indexed for list access
                idx_0_indexed = row_num_1_indexed - 1

                if idx_0_indexed >= len(all_data):
                    logger.warning(f"Row {row_num_1_indexed} is out of bounds for data. Skipping.")
                    continue

                row_data = all_data[idx_0_indexed]

                # Safely get artist and song data
                artist = row_data[artist_col_idx].strip() if artist_col_idx < len(row_data) else ""
                song = row_data[song_col_idx].strip() if song_col_idx < len(row_data) else ""

                # Skip empty rows or rows missing essential data
                if not artist and not song:
                    logger.info(f"Row {row_num_1_indexed}: Skipping empty row")
                    continue

                if not artist or not song:
                    logger.warning(f"Row {row_num_1_indexed}: Missing data - Artist: '{artist}', Song: '{song}'")
                    continue

                logger.info(f"Processing row {row_num_1_indexed}: Artist='{artist}', Song='{song}'")
                processed_count += 1

                # Check if URL already exists in Column K (index 10)
                existing_url = row_data[10].strip() if len(row_data) > 10 else ""
                if existing_url and existing_url != "Not Found":
                    logger.info(f"✅ Row {row_num_1_indexed}: URL already exists: {existing_url}. Skipping search.")
                    found_count += 1
                    continue

                # Search for chord URL
                chord_url = self._search_tab4u(artist, song)

                # Prepare update for batch processing
                if chord_url:
                    updates_batch.append({'range': f'K{row_num_1_indexed}', 'values': [[chord_url]]})
                    logger.info(f"✅ Prepared update for row {row_num_1_indexed} with URL: {chord_url}")
                    found_count += 1
                else:
                    updates_batch.append({'range': f'K{row_num_1_indexed}', 'values': [["Not Found"]]})
                    logger.info(f"❌ Prepared update for row {row_num_1_indexed} with 'Not Found'")

                # Polite delay after each search (not after every row update)
                self._polite_sleep()

            # Apply all updates in a single batch operation
            if updates_batch:
                logger.info(f"Applying {len(updates_batch)} updates to worksheet '{worksheet.title}'...")
                worksheet.batch_update(updates_batch)
                logger.info("✅ All batch updates completed!")
            else:
                logger.info("No updates needed for this worksheet/row range.")


            logger.info(f"Worksheet '{worksheet.title}' processing completed.")
            logger.info(f"📊 Summary for '{worksheet.title}': Processed {processed_count} songs, Found URLs for {found_count} songs")

        except Exception as e:
            logger.error(f"Error processing worksheet '{worksheet.title}': {e}")
            raise


def main():
    """
    Main function to run the scraper.

    Before running this script:
    1. Create a Google Cloud Project
    2. Enable Google Sheets API
    3. Create a service account and download the JSON key file
    4. Share your Google Sheet with the service account email
    5. Update the file paths below
    """

    # Configuration - UPDATE THESE PATHS
    CREDENTIALS_FILE = "credentials.json"

    try:
        scraper = Tab4UScraper(CREDENTIALS_FILE)

        # --- Ask for spreadsheet name ---
        spreadsheet_name = input("Enter the name of your Google Sheet (e.g., 'My Chords'): ").strip()
        try:
            spreadsheet = scraper.gc.open(spreadsheet_name)
            logger.info(f"✅ Google Sheet '{spreadsheet_name}' opened successfully.")
        except gspread.SpreadsheetNotFound:
            logger.error(f"❌ Google Sheet '{spreadsheet_name}' not found. Please check the name and try again.")
            input("Press Enter to exit...")
            return

        # --- Ask for worksheets to process ---
        available_worksheets = [ws.title for ws in spreadsheet.worksheets()]
        logger.info(f"\nAvailable worksheets in '{spreadsheet_name}': {', '.join(available_worksheets)}")
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
                    logger.warning(f"⚠️ Worksheet '{name}' not found. Skipping.")

        if not worksheets_to_process:
            logger.error("No valid worksheets selected or found. Exiting.")
            input("Press Enter to exit...")
            return

        # --- Process each selected worksheet ---
        for ws in worksheets_to_process:
            row_range_input = input(f"\nEnter row range for worksheet '{ws.title}' (e.g., '2-10', '2-end', or 'all'): ").lower().strip()
            if not row_range_input:
                row_range_input = 'all' # Default to all if empty input

            start_row = 2 # Default to start from row 2 (after header)
            end_row = ws.row_count # Default to end of sheet

            if row_range_input != 'all':
                try:
                    if '-' in row_range_input:
                        start_str, end_str = row_range_input.split('-')
                        start_row = int(start_str)
                        if end_str.lower() != 'end':
                            end_row = int(end_str)
                    else: # Single row specified
                        start_row = int(row_range_input)
                        end_row = int(row_range_input)

                    # Basic validation for row numbers
                    if start_row < 1 or end_row < start_row:
                        logger.warning(f"Invalid row range '{row_range_input}'. Processing all rows in '{ws.title}'.")
                        start_row = 2
                        end_row = ws.row_count
                    if start_row == 1: # Warn if starting at header row
                         logger.warning(f"Warning: Starting from row 1 (header row) in '{ws.title}'. Ensure this is intended.")

                except ValueError:
                    logger.warning(f"Invalid row range format '{row_range_input}'. Processing all rows in '{ws.title}'.")
                    start_row = 2
                    end_row = ws.row_count

            # Call the processing function for the current worksheet and determined row range
            scraper.process_worksheet(ws, start_row, end_row)

        logger.info(f"\n🎉 All selected worksheets in '{spreadsheet_name}' processed!")

    except Exception as e:
        logger.error(f"\n❌ An unexpected error occurred in the main script: {e}")
        # Optionally, re-raise if you want the script to terminate with an error code
        # raise

    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
