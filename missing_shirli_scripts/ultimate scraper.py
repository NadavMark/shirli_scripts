import gspread
from google.oauth2.service_account import Credentials
import requests
from bs4 import BeautifulSoup
import time
import random
from urllib.parse import quote_plus, urljoin
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class UltimateGuitarScraper:
    def __init__(self, credentials_path, sheet_url, min_delay=2, max_delay=5):
        """
        Initialize the scraper with Google Sheets credentials and configuration

        Args:
            credentials_path (str): Path to Google Service Account JSON file
            sheet_url (str): URL of the Google Sheet
            min_delay (int): Minimum delay between requests (seconds)
            max_delay (int): Maximum delay between requests (seconds)
        """
        self.credentials_path = credentials_path
        self.sheet_url = sheet_url
        self.min_delay = min_delay
        self.max_delay = max_delay

        # Initialize Google Sheets client
        self.setup_google_sheets()

        # Initialize Selenium WebDriver
        self.setup_webdriver()

    def setup_google_sheets(self):
        """Setup Google Sheets API connection"""
        try:
            # Define the scope for Google Sheets API
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive.file",
                "https://www.googleapis.com/auth/drive"
            ]

            # Load credentials and authorize
            creds = Credentials.from_service_account_file(self.credentials_path, scopes=scope)
            self.client = gspread.authorize(creds)

            # Open the spreadsheet
            self.sheet = self.client.open_by_url(self.sheet_url).worksheet('test')
            logger.info("Successfully connected to Google Sheets")

        except Exception as e:
            logger.error(f"Failed to setup Google Sheets: {e}")
            raise

    def setup_webdriver(self):
        """Setup Selenium WebDriver with Chrome options and better error handling"""
        try:
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager

            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument(
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

            # Use webdriver manager to handle ChromeDriver installation
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)

            # Execute script to remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            logger.info("Successfully initialized WebDriver")

        except Exception as e:
            logger.error(f"Failed to setup WebDriver: {e}")
            raise

    def reinitialize_webdriver(self):
        """Reinitialize WebDriver if connection is lost"""
        try:
            if hasattr(self, 'driver'):
                try:
                    self.driver.quit()
                except:
                    pass

            logger.info("Reinitializing WebDriver...")
            self.setup_webdriver()
            return True

        except Exception as e:
            logger.error(f"Failed to reinitialize WebDriver: {e}")
            return False

    def random_delay(self):
        """Add random delay between requests"""
        delay = random.uniform(self.min_delay, self.max_delay)
        logger.info(f"Waiting {delay:.2f} seconds...")
        time.sleep(delay)

    def search_ultimate_guitar(self, artist, song_title, max_retries=3):
        """
        Search Ultimate Guitar for a specific song with retry logic

        Args:
            artist (str): Artist name
            song_title (str): Song title
            max_retries (int): Maximum number of retries

        Returns:
            str: URL of the best matching chord page, or None if not found
        """
        for attempt in range(max_retries):
            try:
                # Format search query
                search_query = f"{artist} {song_title}"
                search_url = f"https://www.ultimate-guitar.com/search.php?search_type=title&value={quote_plus(search_query)}"

                logger.info(f"Searching for: {search_query} (Attempt {attempt + 1}/{max_retries})")

                # Navigate to search page
                self.driver.get(search_url)
                self.random_delay()

                # Wait for search results to load
                try:
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".dyhP1"))
                    )
                except TimeoutException:
                    logger.warning(f"Search results not found for: {search_query}")
                    if attempt < max_retries - 1:
                        continue
                    return None

                # Parse search results
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                results = self.parse_search_results(soup, artist, song_title)

                if results:
                    return results[0]['url']  # Return the best match
                else:
                    logger.warning(f"No suitable results found for: {search_query}")
                    return None

            except Exception as e:
                logger.error(f"Error searching for {artist} - {song_title} (Attempt {attempt + 1}): {e}")

                if attempt < max_retries - 1:
                    logger.info("Attempting to reinitialize WebDriver...")
                    if self.reinitialize_webdriver():
                        continue
                    else:
                        logger.error("Failed to reinitialize WebDriver")
                        break

        return None

    def parse_search_results(self, soup, target_artist, target_song):
        """
        Parse search results and find the best matching chord page

        Args:
            soup: BeautifulSoup object of the search results page
            target_artist (str): Target artist name
            target_song (str): Target song title

        Returns:
            list: List of matching results sorted by preference
        """
        results = []

        # Find all result rows
        result_rows = soup.find_all('div', class_='dyhP1')

        for row in result_rows[1:]:  # Skip header row
            try:
                # Extract artist
                artist_elem = row.find('span', class_='HV1kd')
                artist = ""
                if artist_elem and artist_elem.find('a'):
                    artist = artist_elem.find('a').get_text(strip=True)

                # Extract song title and URL
                song_elem = row.find('div', class_='qNp1Q SGCxQ')
                if not song_elem:
                    continue

                song_link = song_elem.find('a', class_='WfRYb OtmaM YD9Tl')
                if not song_link:
                    continue

                song_title = song_link.get_text(strip=True)
                url = song_link.get('href')

                # Extract type
                type_elem = row.find_all('div', class_='qNp1Q')[-1]  # Last column is type
                song_type = type_elem.get_text(strip=True) if type_elem else ""

                # Extract rating
                rating_elem = row.find('div', class_='fxXfx')
                rating = 0
                if rating_elem:
                    try:
                        rating = int(rating_elem.get_text(strip=True))
                    except (ValueError, AttributeError):
                        rating = 0

                # Filter results
                if song_type.lower() == 'official':
                    continue  # Skip official versions

                if 'chords' not in song_type.lower():
                    continue  # Only accept chord versions

                # Calculate match score
                score = self.calculate_match_score(artist, song_title, target_artist, target_song, rating)

                if score > 0:
                    results.append({
                        'artist': artist,
                        'song': song_title,
                        'url': urljoin('https://www.ultimate-guitar.com', url) if not url.startswith('http') else url,
                        'type': song_type,
                        'rating': rating,
                        'score': score
                    })

            except Exception as e:
                logger.warning(f"Error parsing result row: {e}")
                continue

        # Sort by score (higher is better)
        results.sort(key=lambda x: x['score'], reverse=True)

        return results

    def calculate_match_score(self, artist, song_title, target_artist, target_song, rating):
        """
        Calculate match score for search results

        Args:
            artist (str): Result artist
            song_title (str): Result song title
            target_artist (str): Target artist
            target_song (str): Target song title
            rating (int): Rating of the result

        Returns:
            int: Match score (higher is better)
        """
        score = 0

        # Normalize strings for comparison
        def normalize(text):
            return re.sub(r'[^\w\s]', '', text.lower()).strip()

        norm_artist = normalize(artist)
        norm_song = normalize(song_title)
        norm_target_artist = normalize(target_artist)
        norm_target_song = normalize(target_song)

        # Song title match (most important)
        if norm_target_song in norm_song or norm_song in norm_target_song:
            score += 1000

            # Exact song match bonus
            if norm_target_song == norm_song:
                score += 500
        else:
            return 0  # If song doesn't match, skip

        # Artist match bonus
        if norm_target_artist in norm_artist or norm_artist in norm_target_artist:
            score += 2000  # Same artist is highly preferred

            # Exact artist match bonus
            if norm_target_artist == norm_artist:
                score += 1000

        # Rating bonus (up to 100 points)
        score += min(rating, 100)

        return score

    def get_sheet_data(self, start_row=2, end_row=None):
        """
        Get data from Google Sheet

        Args:
            start_row (int): Starting row number (1-indexed)
            end_row (int): Ending row number (1-indexed), None for all rows

        Returns:
            list: List of row data
        """
        try:
            if end_row is None:
                all_values = self.sheet.get_all_values()
                end_row = len(all_values)

            # Get the range of data
            range_name = f'A{start_row}:F{end_row}'
            values = self.sheet.batch_get([range_name])[0]

            return values

        except Exception as e:
            logger.error(f"Error getting sheet data: {e}")
            return []

    def update_chord_cell(self, row_num, url):
        """
        Update the chord URL in column F

        Args:
            row_num (int): Row number (1-indexed)
            url (str): URL to insert
        """
        try:
            # Use the correct format for gspread update
            self.sheet.update(f'F{row_num}', [[url]])
            logger.info(f"Updated row {row_num} with URL: {url}")

        except Exception as e:
            logger.error(f"Error updating row {row_num}: {e}")
            # Try alternative method
            try:
                self.sheet.update_cell(row_num, 6, url)  # Column F is index 6
                logger.info(f"Updated row {row_num} with URL using alternative method: {url}")
            except Exception as e2:
                logger.error(f"Alternative update method also failed for row {row_num}: {e2}")

    def process_rows(self, start_row=2, end_row=None, rows_to_process=None):
        """
        Process rows to find and update chord URLs

        Args:
            start_row (int): Starting row number
            end_row (int): Ending row number (None for all)
            rows_to_process (list): Specific row numbers to process (overrides start/end)
        """
        try:
            if rows_to_process:
                # Process specific rows
                for row_num in rows_to_process:
                    row_data = self.sheet.row_values(row_num)
                    self.process_single_row(row_data, row_num)
                    self.random_delay()
            else:
                # Process range of rows
                data = self.get_sheet_data(start_row, end_row)

                for i, row_data in enumerate(data):
                    current_row = start_row + i
                    self.process_single_row(row_data, current_row)
                    self.random_delay()

        except Exception as e:
            logger.error(f"Error processing rows: {e}")
        finally:
            self.cleanup()

    def process_single_row(self, row_data, row_num):
        """
        Process a single row to find and update chord URL

        Args:
            row_data (list): Row data from the sheet
            row_num (int): Row number (1-indexed)
        """
        try:
            # Ensure we have enough columns
            while len(row_data) < 6:
                row_data.append('')

            artist = row_data[0].strip() if len(row_data) > 0 else ''
            song_title = row_data[1].strip() if len(row_data) > 1 else ''
            chords_cell = row_data[5].strip() if len(row_data) > 5 else ''

            # Skip if artist or song title is empty
            if not artist or not song_title:
                logger.info(f"Row {row_num}: Skipping - missing artist or song title")
                return

            # Check if we need to process this row
            if chords_cell and chords_cell.lower() != 'not found' and chords_cell.startswith('http'):
                logger.info(f"Row {row_num}: Skipping - already has URL")
                return

            logger.info(f"Row {row_num}: Processing {artist} - {song_title}")

            # Search for chord URL
            url = self.search_ultimate_guitar(artist, song_title)

            if url:
                # Try to update the cell
                success = False
                for attempt in range(3):  # Try up to 3 times
                    try:
                        self.update_chord_cell(row_num, url)
                        success = True
                        logger.info(f"Row {row_num}: Successfully found and updated URL")
                        break
                    except Exception as e:
                        logger.warning(f"Row {row_num}: Update attempt {attempt + 1} failed: {e}")
                        if attempt < 2:
                            time.sleep(2)  # Wait before retry

                if not success:
                    logger.error(f"Row {row_num}: Failed to update after 3 attempts")
            else:
                # Try to update with "Not Found"
                try:
                    self.update_chord_cell(row_num, 'Not Found')
                    logger.info(f"Row {row_num}: No results found, marked as 'Not Found'")
                except Exception as e:
                    logger.error(f"Row {row_num}: Failed to update with 'Not Found': {e}")

        except Exception as e:
            logger.error(f"Error processing row {row_num}: {e}")

    def cleanup(self):
        """Clean up resources"""
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
                logger.info("WebDriver closed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


def main():
    """
    Main function to run the scraper
    """
    # Configuration
    CREDENTIALS_PATH = "credentials.json"  # Update this path
    SHEET_URL = "https://docs.google.com/spreadsheets/d/10BK4b1_w1iInxgDL-cDgWtK776PsqxXlspZqjNFrj3Y/edit?gid=1604461382#gid=1604461382"  # Update this URL

    # Initialize scraper
    scraper = UltimateGuitarScraper(
        credentials_path=CREDENTIALS_PATH,
        sheet_url=SHEET_URL,
        min_delay=2,  # Minimum delay between requests
        max_delay=5  # Maximum delay between requests
    )

    # Option 1: Process all rows starting from row 2
    # scraper.process_rows(start_row=2)

    # Option 2: Process specific range of rows
    # scraper.process_rows(start_row=2, end_row=10)

    # Option 3: Process specific row numbers
    scraper.process_rows(rows_to_process=[2, 3, 4, 5])

    print("Processing completed!")


if __name__ == "__main__":
    main()
