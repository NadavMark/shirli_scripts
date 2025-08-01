import gspread
import time
import random
import sys
from ytmusicapi import YTMusic
from gspread.exceptions import APIError

# --- Configuration ---
GOOGLE_SHEET_NAME = 'songs'
WORKSHEET_NAME = 'songs1'
CREDENTIALS_FILE = 'credentials.json'
YTMUSIC_AUTH_FILE = 'headers_auth1.json' # This file needs to be generated by manually extracting headers
LOG_FILE = 'progress.log'

# Column assignments (1-indexed)
ARTIST_COLUMN = 1   # Column A
SONG_TITLE_COLUMN = 2 # Column B
YOUTUBE_LINK_COLUMN = 5 # Column E (header 'youtube')

MIN_DELAY = 5 # seconds
MAX_DELAY = 12 # seconds
MAX_RETRIES = 3 # for API calls
RETRY_BACKOFF_FACTOR = 2 # for exponential backoff

# --- Helper Functions ---

def get_last_processed_row():
  """Reads the last processed row number from the log file."""
  try:
      with open(LOG_FILE, 'r') as f:
          return int(f.read().strip())
  except (FileNotFoundError, ValueError):
      return 1 # Start from row 1 if no log or invalid content

def save_last_processed_row(row_number):
  """Saves the last processed row number to the log file."""
  with open(LOG_FILE, 'w') as f:
      f.write(str(row_number))

def retry_api_call(func, *args, **kwargs):
  """
  Retries an API call with exponential backoff.
  Handles gspread.exceptions.APIError and general exceptions.
  """
  for attempt in range(MAX_RETRIES):
      try:
          result = func(*args, **kwargs)
          return result
      except APIError as e:
          if "quotaExceeded" in str(e):
              print(f"\n--- Google Sheets API Quota Exceeded! ---")
              print(f"Error: {e}")
              print(f"Please wait for your quota to reset (usually 24 hours).")
              print(f"The script will exit. You can resume from the last logged row.")
              sys.exit(1) # Exit script if quota is exceeded
          else:
              print(f"Google Sheets API Error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
      except Exception as e:
          print(f"General API Error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")

      if attempt < MAX_RETRIES - 1:
          sleep_time = RETRY_BACKOFF_FACTOR ** attempt + random.uniform(0, 1)
          print(f"Retrying in {sleep_time:.2f} seconds...")
          time.sleep(sleep_time)
      else:
          raise # Re-raise the last exception if all retries fail
  return None # Should not be reached

def search_youtube_music_with_retry(ytmusic, query):
  """
  Searches YouTube Music with retry logic and random delay.
  Returns the videoId if found, otherwise None.
  """
  for attempt in range(MAX_RETRIES):
      try:
          results = ytmusic.search(query, filter='songs')
          if results:
              # Prioritize results that have a videoId (actual YouTube video)
              for result in results:
                  if 'videoId' in result and result['videoId']:
                      return result['videoId']
              # Fallback to first result if no videoId found in initial loop
              if 'videoId' in results[0] and results[0]['videoId']:
                  return results[0]['videoId']
          return None
      except Exception as e:
          print(f"YTMusicAPI Error for '{query}' (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
          if attempt < MAX_RETRIES - 1:
              sleep_time = RETRY_BACKOFF_FACTOR ** attempt + random.uniform(0, 1)
              print(f"Retrying in {sleep_time:.2f} seconds...")
              time.sleep(sleep_time)
          else:
              print(f"Failed to search for '{query}' after {MAX_RETRIES} attempts.")
              return None # Return None if all retries fail

# --- Main Script ---
def main():
  print("Starting YouTube Music Link Retriever...")

  # 1. Authenticate with Google Sheets
  try:
      gc = gspread.service_account(filename=CREDENTIALS_FILE)
      spreadsheet = gc.open(GOOGLE_SHEET_NAME)
      worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
      print(f"Successfully connected to Google Sheet '{GOOGLE_SHEET_NAME}', worksheet '{WORKSHEET_NAME}'.")
  except FileNotFoundError:
      print(f"Error: Google Sheets credentials file '{CREDENTIALS_FILE}' not found.")
      print("Please ensure the file exists and is in the correct directory.")
      sys.exit(1)
  except Exception as e:
      print(f"Error connecting to Google Sheets: {e}")
      print("Please check your sheet name, worksheet name, and permissions for the service account.")
      sys.exit(1)

  # Verify header for YouTube links
  try:
      header_cell = worksheet.cell(1, YOUTUBE_LINK_COLUMN).value
      if header_cell != 'youtube':
          print(f"Warning: Header in column {chr(64 + YOUTUBE_LINK_COLUMN)} (row 1) is '{header_cell}', expected 'youtube'.")
          print("Please ensure the header is correct or adjust YOUTUBE_LINK_COLUMN.")
  except Exception as e:
      print(f"Error reading header cell: {e}")
      sys.exit(1)

  # 2. Authenticate with YTMusicAPI
  try:
      ytmusic = YTMusic(YTMUSIC_AUTH_FILE)
      print(f"Successfully authenticated with YTMusicAPI using '{YTMUSIC_AUTH_FILE}'.")
  except FileNotFoundError:
      print(f"Error: YTMusicAPI authentication file '{YTMUSIC_AUTH_FILE}' not found.")
      print("Please ensure you have created it manually as per the instructions.")
      sys.exit(1)
  except Exception as e:
      print(f"Error initializing YTMusicAPI: {e}")
      print("Please check your authentication file content and internet connection.")
      sys.exit(1)

  # 3. Get rows to process from user
  last_processed = get_last_processed_row()
  print(f"Last successfully processed row: {last_processed}")

  while True:
      try:
          start_row_input = input(f"Enter the starting row to process (default: {last_processed + 1}): ")
          start_row = int(start_row_input) if start_row_input else last_processed + 1
          if start_row < 2: # Data starts from row 2, row 1 is header
              print("Starting row cannot be less than 2 (header row). Setting to 2.")
              start_row = 2
          break
      except ValueError:
          print("Invalid input. Please enter a number.")

  while True:
      try:
          end_row_input = input("Enter the ending row to process (leave empty to process all remaining rows): ")
          end_row = int(end_row_input) if end_row_input else None
          if end_row is not None and end_row < start_row:
              print("Ending row cannot be less than starting row. Please re-enter.")
          else:
              break
      except ValueError:
          print("Invalid input. Please enter a number.")

  print(f"Processing rows from {start_row} to {'end' if end_row is None else end_row}...")

  # 4. Process rows
  current_row = start_row
  try:
      # Fetch all values once for efficiency, then iterate
      all_values = worksheet.get_all_values()
      max_sheet_row = len(all_values)

      if end_row is None:
          end_row = max_sheet_row

      if start_row > max_sheet_row:
          print(f"Starting row {start_row} is beyond the last row in the sheet ({max_sheet_row}). No rows to process.")
          return

      for r_idx in range(start_row - 1, min(end_row, max_sheet_row)): # r_idx is 0-indexed for list
          current_row = r_idx + 1 # current_row is 1-indexed for sheet
          row_data = all_values[r_idx]

          # Extract song title and artist name, handling potential missing columns
          # Python's string handling and these libraries are Unicode-aware,
          # so Hebrew characters are processed correctly.
          song_title = row_data[SONG_TITLE_COLUMN - 1].strip() if len(row_data) >= SONG_TITLE_COLUMN else ""
          artist_name = row_data[ARTIST_COLUMN - 1].strip() if len(row_data) >= ARTIST_COLUMN else ""

          # Construct search query based on the preferred "Artist - Song Title" format
          search_query = ""
          if artist_name and song_title:
              search_query = f"{artist_name} - {song_title}"
          elif artist_name:
              search_query = artist_name
          elif song_title:
              search_query = song_title
          # The 'else' case (both empty) is handled by the next check

          if not search_query:
              print(f"Skipping row {current_row}: Empty search query after checking song title and artist.")
              save_last_processed_row(current_row)
              continue

          existing_link = ""
          if len(row_data) >= YOUTUBE_LINK_COLUMN:
              existing_link = row_data[YOUTUBE_LINK_COLUMN - 1].strip()

          if existing_link and "youtube.com/watch" in existing_link:
              print(f"Row {current_row}: '{search_query}' already has a YouTube link. Skipping.")
              save_last_processed_row(current_row)
              continue

          print(f"Processing row {current_row}: Searching for '{search_query}'...")
          video_id = search_youtube_music_with_retry(ytmusic, search_query)

          if video_id:
              youtube_link = f"https://music.youtube.com/watch?v={video_id}"
              print(f"Found link: {youtube_link}")
              retry_api_call(worksheet.update_cell, current_row, YOUTUBE_LINK_COLUMN, youtube_link)
              print(f"Updated row {current_row}.")
          else:
              print(f"No YouTube link found for '{search_query}'.")
              # Optionally, write a placeholder or leave blank
              # retry_api_call(worksheet.update_cell, current_row, YOUTUBE_LINK_COLUMN, "NOT FOUND")

          save_last_processed_row(current_row)

          # Add random delay between requests
          delay = random.uniform(MIN_DELAY, MAX_DELAY)
          print(f"Waiting for {delay:.2f} seconds...")
          time.sleep(delay)

  except Exception as e:
      print(f"\nAn unexpected error occurred at row {current_row}: {e}")
      print(f"The script stopped. Last successfully processed row was {current_row - 1}.")
      print("You can resume from this row in the next run.")
  finally:
      print("\nScript finished or stopped.")
      print(f"Last processed row logged: {get_last_processed_row()}")

if __name__ == "__main__":
  main()
