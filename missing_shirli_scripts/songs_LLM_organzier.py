import gspread
import pandas as pd
from googleapiclient.discovery import build
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import time
import re
import os

# Import your LLM client library
# For OpenAI:
# from openai import OpenAI
# For Google Gemini:
import google.generativeai as genai

# Load configurations
from config import (
    GOOGLE_SHEETS_SERVICE_ACCOUNT_FILE,
    GOOGLE_SHEETS_SPREADSHEET_ID,
    YOUTUBE_API_KEY,
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    LLM_API_KEY
)

# --- 1. Initialize API Clients ---

# Google Sheets
try:
    gc = gspread.service_account(filename=GOOGLE_SHEETS_SERVICE_ACCOUNT_FILE)
    spreadsheet = gc.open_by_key(GOOGLE_SHEETS_SPREADSHEET_ID)
    worksheet = spreadsheet.worksheet('Cleaned_Songs_Data')  # Or by index, e.g., spreadsheet.get_worksheet(0)
    print("Successfully connected to Google Sheet.")
except Exception as e:
    print(f"Error connecting to Google Sheet: {e}")
    exit()

# YouTube API
youtube_service = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
print("YouTube API client initialized.")

# Spotify API
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID,
                                                           client_secret=SPOTIFY_CLIENT_SECRET))
print("Spotify API client initialized.")

# LLM Client
# For OpenAI:
# client_llm = OpenAI(api_key=LLM_API_KEY)
# For Google Gemini:
genai.configure(api_key=LLM_API_KEY)
llm_model = genai.GenerativeModel('gemini-1.5-pro')  # Or your preferred Gemini model
print("LLM client initialized.")


# --- 2. Helper Functions for API Interactions ---

def get_youtube_metadata_from_url(url):
    """Extracts artist and title from a YouTube video URL."""
    if not url or "youtube.com/watch?v=" not in url:
        return None, None
    video_id_match = re.search(r"v=([^&]+)", url)
    if not video_id_match:
        return None, None
    video_id = video_id_match.group(1)
    try:
        request = youtube.videos().list(
            part="snippet",
            id=video_id
        )
        response = request.execute()
        if response and response['items']:
            snippet = response['items'][0]['snippet']
            title = snippet.get('title', '')
            channel_title = snippet.get('channelTitle', '')  # Often the artist's channel name
            return channel_title, title  # This might need refinement for accurate artist
        return None, None
    except Exception as e:
        print(f"Error fetching YouTube metadata for {url}: {e}")
        return None, None


def get_spotify_metadata_from_url(url):
    """Extracts artist and title from a Spotify track URL."""
    if not url or "open.spotify.com/track/" not in url:
        return None, None
    track_id_match = re.search(r"track/([^?]+)", url)
    if not track_id_match:
        return None, None
    track_id = track_id_match.group(1)
    try:
        track_info = sp.track(track_id)
        if track_info:
            artist_name = track_info['artists'][0]['name'] if track_info['artists'] else None
            song_title = track_info['name']
            return artist_name, song_title
        return None, None
    except Exception as e:
        print(f"Error fetching Spotify metadata for {url}: {e}")
        return None, None


def search_youtube(artist, song_title, youtube_client):
    """Searches YouTube for official video/audio by artist and song title."""
    query = f"{artist} - {song_title} official"
    try:
        request = youtube_client.search().list(
            q=query,
            part="snippet",
            type="video",
            maxResults=5  # Get a few results to pick the best
        )
        response = request.execute()

        # Prioritize official channels, official video/audio, lyric video
        best_link = None
        for item in response['items']:
            video_title = item['snippet']['title'].lower()
            channel_title = item['snippet']['channelTitle'].lower()
            video_id = item['id']['videoId']
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            # Basic official channel heuristic (can be improved)
            is_official_channel_match = (artist.lower().replace(" ", "") in channel_title.replace(" ", "") or
                                         channel_title.endswith("official artist channel") or
                                         channel_title.endswith("vevo"))

            if "official video" in video_title or "official audio" in video_title:
                return video_url  # Strong match, return immediately
            elif "lyric video" in video_title and is_official_channel_match:
                best_link = video_url  # Good candidate, but keep looking for "official"
            elif is_official_channel_match and not best_link:  # If official channel, and no better link found yet
                best_link = video_url

        return best_link if best_link else (
            f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}" if response['items'] else None)

    except Exception as e:
        print(f"Error searching YouTube for '{artist} - {song_title}': {e}")
        return None


def search_spotify(artist, song_title):
    """Searches Spotify for a track by artist and song title."""
    try:
        results = sp.search(q=f"track:{song_title} artist:{artist}", type="track", limit=5)
        if results and results['tracks']['items']:
            for track in results['tracks']['items']:
                # Basic check: artist name should be in the track's artist list
                track_artists = [a['name'].lower() for a in track['artists']]
                if artist.lower() in track_artists:
                    # You might want to add more sophisticated matching here, e.g.,
                    # checking for exact title match, popularity, etc.
                    return track['external_urls']['spotify']
            # Fallback if no exact artist match in the top results
            return results['tracks']['items'][0]['external_urls']['spotify']
        return None
    except Exception as e:
        print(f"Error searching Spotify for '{artist} - {song_title}': {e}")
        return None


# --- 3. LLM Function for Lyric Identification and Artist Verification ---

def llm_process_song_info(artist, song_title_or_lyrics):
    """
    Uses LLM to identify song from lyrics and verify/correct artist.
    Returns (corrected_artist, corrected_song_title, confidence_score, explanation)
    """
    prompt = f"""
    אתה עוזר מוזיקה מומחה. משימתך היא לנתח מידע על שירים, במיוחד שירים בעברית של אמנים ישראלים, ולספק נתונים מדויקים ומאומתים.

    **נתוני קלט:**
    - **שם אמן (Column A):** שם האמן הנוכחי המשויך לשיר.
    - **טקסט שיר (Column B):** זה יכול להיות שם השיר הרשמי, או קטע מילים מתוך שיר של האמן המוזכר בעמודה A.
    - **הערות נוספות (Column C):** מידע קונטקסטואלי נוסף (לדוגמה: נושאים, אירועים).
    - **קישור (Column D):** קישור ליוטיוב או ספוטיפיי. (שים לב: הנתונים מהקישור [אמן+כותרת] יועברו אליך כבר כטקסט בעמודות A ו-B, אם זוהו).

    **הוראות עיבוד:**
    1.  **זיהוי מדויק של שם השיר מתוך טקסט/קטע מילים:**
        * נתח את "טקסט שיר". אם זהו קטע מילים או ביטוי לירי: **זהה בוודאות את שם השיר הרשמי** של האמן המצוין ב"שם אמן". אם קטע המילים שייך לשיר אחר לגמרי, ציין את השיר הנכון ואת האמן המקורי שלו.
        * אם "טקסט שיר" הוא כבר שם שיר רשמי ומלא עבור האמן הנתון: **אשר אותו כפי שהוא**.
        * אם אינך יכול לזהות בוודאות שם שיר רשמי מקטע המילים, או אם "טקסט שיר" נראה בלתי קשור לחלוטין לאמן (לדוגמה, טקסט אקראי), ציין "N/A" עבור שם השיר וסמן את רמת הביטחון כ"נמוכה".

    2.  **אימות ותיקון ייחוס אמן:**
        * בהתבסס על **שם השיר הרשמי שזוהה** (משלב 1), וודא אם "שם אמן" הוא **האמן המבצע המקורי או הראשי** של השיר הספציפי הזה.
        * **אם השיר הוא גרסת כיסוי ידועה של "שם אמן" הנתון**, וגרסת הכיסוי הזו מוכרת ונבדלת, **שמור על "שם אמן" הנתון** וציין שמדובר בגרסת כיסוי.
        * **אם השיר ידוע בעיקר כשיר של אמן מקורי או ראשי *אחר***, ו"שם אמן" הנתון הוא ייחוס שגוי או גרסת כיסוי לא מוכרת, **הצע את שם האמן המקורי או הראשי הנכון**.
        * **אם "שם אמן" נכון והשיר הוא יצירה מקורית שלהם**, אשר זאת.
        * אם אינך יכול לקבוע או לאמת בוודאות את האמן, ציין "N/A" עבור האמן וסמן את רמת הביטחון כ"נמוכה".

    3.  **רמת ביטחון והסבר:**
        * הקצה רמת `confidence` ("גבוהה", "בינונית", או "נמוכה") המציינת את מידת וודאותך לגבי שם השיר שזוהה והאמן המתוקן.
        * **אם רמת הביטחון "נמוכה"**, הוסף הערה קצרה (עד 10 מילים) בתוך שדה ה-`explanation` המציינת את הסיבה, לדוגמה: "לא ניתן לזהות בוודאות את השיר/אמן."
        * ספק `explanation` קצר המצדיק את הזיהוי או התיקון שלך. לדוגמה: "זוהה 'מלכת היופי של מיאמי' מתוך מילים. יהורם גאון הוא האמן המקורי." או "אושר 'מה שאת אוהבת'. גלי עטרי היא האמנית המבצעת, אך השם הרשמי קצר יותר."

    **פורמט פלט:**
    ספק את תגובתך אך ורק כאובייקט JSON, בהתאם לסכימה הבאה:
    ```json
    {{
        "identified_song_title": "שם השיר הרשמי כאן (או N/A אם לא בטוח)",
        "corrected_artist": "שם האמן הנכון/מקורי/כיסוי כאן (או N/A אם לא בטוח)",
        "is_cover_version": true/false,
        "confidence": "גבוהה/בינונית/נמוכה",
        "explanation": "הסבר קצר לזיהוי/תיקון."
    }}
    ```

    **Examples (for better few-shot learning - you would add these):**

    **Example 1: Lyrical Snippet**
    Input:
    Artist: "Queen"
    Song Text: "Is this the real life? Is this just fantasy?"
    Output:
    ```json
    {{
        "identified_song_title": "Bohemian Rhapsody",
        "corrected_artist": "Queen",
        "is_cover_version": false,
        "confidence": "high",
        "explanation": "Identified 'Bohemian Rhapsody' from lyrics. Queen is the original artist."
    }}
    ```

    **Example 2: Correct Title**
    Input:
    Artist: "Adele"
    Song Text: "Rolling in the Deep"
    Output:
    ```json
    {{
        "identified_song_title": "Rolling in the Deep",
        "corrected_artist": "Adele",
        "is_cover_version": false,
        "confidence": "high",
        "explanation": "Confirmed 'Rolling in the Deep'. Adele is the original artist."
    }}
    ```

    **Example 3: Well-known Cover**
    Input:
    Artist: "Jeff Buckley"
    Song Text: "I heard there was a secret chord, that David played and it pleased the Lord"
    Output:
    ```json
    {{
        "identified_song_title": "Hallelujah",
        "corrected_artist": "Jeff Buckley",
        "is_cover_version": true,
        "confidence": "high",
        "explanation": "Identified 'Hallelujah' as a cover by Jeff Buckley, originally by Leonard Cohen."
    }}
    ```

    **Example 4: Misattributed Artist**
    Input:
    Artist: "Some Random Artist"
    Song Text: "Billie Jean"
    Output:
    ```json
    {{
        "identified_song_title": "Billie Jean",
        "corrected_artist": "Michael Jackson",
        "is_cover_version": false,
        "confidence": "high",
        "explanation": "Identified 'Billie Jean'. Michael Jackson is the original artist, 'Some Random Artist' is incorrect."
    }}
    ```

    **Example 5: Ambiguous/Unrelated Lyric/Text**
    Input:
    Artist: "Imagine Dragons"
    Song Text: "The quick brown fox jumps over the lazy dog"
    Output:
    ```json
    {{
        "identified_song_title": "N/A",
        "corrected_artist": "N/A",
        "is_cover_version": false,
        "confidence": "low",
        "explanation": "Song text appears to be unrelated to music or artist. Cannot confidently identify."
    }}
    ```

    **Example 1: Lyrical Snippet שגוי, אמן שגוי**
    קלט:
    Artist: "דפנה ארמוני"
    Song Text: "עוד תראה כמה טוב יהיה"
    Output:
    ```json
    {{
        "identified_song_title": "בשנה הבאה",
        "corrected_artist": "נעמי שמר",
        "is_cover_version": false,
        "confidence": "גבוהה",
        "explanation": "הקטע 'עוד תראה כמה טוב יהיה' שייך לשיר 'בשנה הבאה' של נעמי שמר. האמן שגוי."
    }}
    ```

    **Example 2: זיהוי מקישור (נתונים מועברים כטקסט)**
    קלט:
    Artist: "דני רובס ושלמה גרוניך"
    Song Text: "אנ'לא פוחד כמה כבר מכלום"
    Output:
    ```json
    {{
        "identified_song_title": "אנ'לא פוחד כמה כבר מכלום",
        "corrected_artist": "דני רובס ושלמה גרוניך",
        "is_cover_version": false,
        "confidence": "גבוהה",
        "explanation": "אושר 'אנ'לא פוחד כמה כבר מכלום'. דני רובס ושלמה גרוניך הם האמנים המקוריים."
    }}
    ```

    **Example 3: שם שיר רשמי שונה מקטע מילים**
    קלט:
    Artist: "גלי עטרי"
    Song Text: "תעשי רק מה שאת אוהבת"
    Output:
    ```json
    {{
        "identified_song_title": "מה שאת אוהבת",
        "corrected_artist": "גלי עטרי",
        "is_cover_version": false,
        "confidence": "גבוהה",
        "explanation": "זוהה 'מה שאת אוהבת' מתוך המילים. גלי עטרי היא האמנית המקורית."
    }}
    ```

    **Example 4: קטע מילים לא מזוהה / אמן לא מזוהה**
    קלט:
    Artist: "לא זוהה"
    Song Text: "לא מזוהה"
    Output:
    ```json
    {{
        "identified_song_title": "N/A",
        "corrected_artist": "N/A",
        "is_cover_version": false,
        "confidence": "נמוכה",
        "explanation": "לא ניתן לזהות בוודאות את השיר או האמן מתוך הנתונים."
    }}
    ```

    **Example 5: קטע מילים תקין, אמן תקין**
    קלט:
    Artist: "שלמה ארצי"
    Song Text: "אני נושא עימי אלף זכרונות"
    Output:
    ```json
    {{
        "identified_song_title": "אני נושא עימי",
        "corrected_artist": "שלמה ארצי",
        "is_cover_version": false,
        "confidence": "גבוהה",
        "explanation": "זוהה 'אני נושא עימי' מתוך המילים. שלמה ארצי הוא האמן המקורי."
    }}
    ```

    **Example 6: שם שיר רשמי מלא, אמן תקין**
    קלט:
    Artist: "עידן רייכל"
    Song Text: "ממעמקים"
    Output:
    ```json
    {{
        "identified_song_title": "ממעמקים",
        "corrected_artist": "הפרויקט של עידן רייכל",
        "is_cover_version": false,
        "confidence": "גבוהה",
        "explanation": "אושר 'ממעמקים'. הפרויקט של עידן רייכל הוא האמן המקורי."
    }}
    ```
    """
    # For Google Gemini
    try:
        response = llm_model.generate_content(prompt)
        # Assuming the LLM responds with a string that can be parsed as JSON
        llm_output_text = response.text.strip()
        # Clean up common LLM output issues (e.g., markdown code blocks)
        if llm_output_text.startswith("```json"):
            llm_output_text = llm_output_text[7:]
        if llm_output_text.endswith("```"):
            llm_output_text = llm_output_text[:-3]

        llm_data = json.loads(llm_output_text)
        return (llm_data.get('corrected_artist'),
                llm_data.get('identified_song_title'),
                llm_data.get('confidence'),
                llm_data.get('explanation'))
    except Exception as e:
        print(f"Error calling LLM for '{artist} - {song_title_or_lyrics}': {e}")
        return None, None, "low", f"LLM error: {e}"


# --- 4. Main Processing Logic ---

def process_song_data():
    data = worksheet.get_all_values()
    headers = data[0]
    df = pd.DataFrame(data[1:], columns=headers)

    # Add 'Notes' column if it doesn't exist
    if 'Notes' not in df.columns:
        df['Notes'] = ''

    # Iterate through each row using df.iterrows() for easy updates
    for index, row in df.iterrows():
        original_artist = row['Artist']
        original_song_title = row['Song Title']
        tags = row['Tags']
        youtube_link = row['YouTube Link']
        spotify_link = row[' Spotify Link']
        notes = row['Notes']

        print(f"\nProcessing row {index + 2}: Artist='{original_artist}', Song='{original_song_title}'")

        current_artist = original_artist
        current_song_title = original_song_title

        # 1. Handle Rows with Links but Missing Song/Artist Data
        if (not current_artist or not current_song_title) and (youtube_link or spotify_link):
            if youtube_link and (not current_artist or not current_song_title):
                yt_artist, yt_title = get_youtube_metadata_from_url(youtube_link)
                if yt_artist and yt_title:
                    current_artist = current_artist or yt_artist
                    current_song_title = current_song_title or yt_title
                    notes += f" (Retrieved A/B from YouTube link)"

            if spotify_link and (not current_artist or not current_song_title):
                sp_artist, sp_title = get_spotify_metadata_from_url(spotify_link)
                if sp_artist and sp_title:
                    current_artist = current_artist or sp_artist
                    current_song_title = current_song_title or sp_title
                    notes += f" (Retrieved A/B from Spotify link)"

            if not current_artist or not current_song_title:
                notes += f" (Could not fully populate A/B from provided links)"

        # 2. Handle Rows with Full Song/Artist Information (or now populated)
        if current_artist and current_song_title:
            # Step 2.1 & 2.3: Identify Song from Lyrics & Verify/Correct Artist using LLM
            llm_artist, llm_song, confidence, explanation = llm_process_song_info(current_artist, current_song_title)

            if confidence != "low" and llm_song != "N/A" and llm_artist != "N/A":
                if llm_song and llm_song != current_song_title:
                    notes += f" (Song title corrected from '{current_song_title}' to '{llm_song}' based on lyrics and LLM. {explanation})"
                    current_song_title = llm_song
                if llm_artist and llm_artist != current_artist:
                    notes += f" (Artist corrected from '{current_artist}' to '{llm_artist}' by LLM for original. {explanation})"
                    current_artist = llm_artist
            else:
                notes += f" (LLM uncertain about song/artist: {explanation})"

            # Step 2.2 & 2.4: Search for and Update Links
            found_yt_link = search_youtube(current_artist, current_song_title, youtube_service)
            found_sp_link = search_spotify(current_artist, current_song_title)

            if found_yt_link and found_yt_link != youtube_link and "google.com/results" not in found_yt_link:
                youtube_link = found_yt_link
            elif youtube_link and "google.com/results" in youtube_link:  # Clear old Google search links
                youtube_link = ""
            elif not found_yt_link:
                youtube_link = ""  # Clear if no verified link found

            if found_sp_link and found_sp_link != spotify_link:
                spotify_link = found_sp_link
            elif not found_sp_link:
                spotify_link = ""  # Clear if no verified link found

        else:
            notes += " (Insufficient data for full processing)"

        # Update DataFrame row
        df.at[index, 'Artist'] = current_artist
        df.at[index, 'Song Title'] = current_song_title
        df.at[index, 'YouTube Link'] = youtube_link
        df.at[index, 'Spotify Link'] = spotify_link
        df.at[index, 'Notes'] = notes

        # Add a delay to avoid hitting API rate limits
        time.sleep(1.5)  # Adjust as needed for your API quotas

    # Write the updated DataFrame back to the Google Sheet
    # Clear existing data and then write headers + df.values.tolist()
    worksheet.clear()
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())
    print("\nProcessing complete. Google Sheet updated.")


if __name__ == '__main__':
    process_song_data()