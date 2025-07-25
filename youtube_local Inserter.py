import re
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- Configuration ---
CREDS_FILE = 'credentials.json'
SPREADSHEET_ID = '10BK4b1_w1iInxgDL-cDgWtK776PsqxXlspZqjNFrj3Y'
WORKSHEET_NAME = 'songs1'  # Use 'songs1' as specified

# --- Text Content (Replace with your actual text file reading) ---
# For demonstration, I'm putting the text directly here.
# In a real scenario, you'd read this from a file, e.g.,:
# with open('your_log_file.txt', 'r', encoding='utf-8') as f:
#     log_text = f.read()

log_text = """🎼 (1) Processing Row 23: 'געגועים לבני אדם' by 'חנן בן ארי'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=G9m54DdWgoo

🎼 (2) Processing Row 24: 'Si tous les oiseaux' by 'Les Compagnons de la chanson'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=ltvF0faSKjA

🎼 (3) Processing Row 25: 'תרקדי את הלילה' by 'אבי טולדנו'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube: No definitive match found.

🎼 (4) Processing Row 26: 'אל תירא' by 'אביהו מדינה'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube: No definitive match found.

🎼 (5) Processing Row 27: 'אל תשליכני לעת זקנה' by 'אביהו מדינה'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=nrcFgWG9bR4

🎼 (6) Processing Row 28: 'מתי נתנשק' by 'אביתר בנאי'
   🔍 Searching Spotify...
   🎵 Spotify (Exact Match): https://open.spotify.com/track/57aqwB6tGV9XdxcvlEqPAn
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=mwFjgtidDDA

🎼 (7) Processing Row 29: 'אני כאן' by 'אביתר בנאי'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=r5R0FysPU34

🎼 (8) Processing Row 30: 'חלפו ימיי ולילותי' by 'אבנר גדסי'
   🔍 Searching Spotify...
   🎵 Spotify: No definitive match found.
   🔍 Searching YouTube...
   📺 YouTube: No definitive match found.

🎼 (9) Processing Row 31: 'מי לא יבוא' by 'אברהם טל ובניה ברבי'
   🔍 Searching Spotify...
   🎵 Spotify: No definitive match found.
   🔍 Searching YouTube...
   📺 YouTube: No definitive match found.

🎼 (10) Processing Row 32: 'עלה קטן' by 'אברהם פריד'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube: No definitive match found.

🎼 (11) Processing Row 33: 'בפאתי הכפר 1955' by 'אהובה צדוק'
   🔍 Searching Spotify...
   🎵 Spotify: No definitive match found.
   🔍 Searching YouTube...
   📺 YouTube: No definitive match found.

🎼 (12) Processing Row 34: 'אל תפחד' by 'אהוד בנאי'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=DifgJhL-fLU

🎼 (13) Processing Row 35: 'היום הרת עולם' by 'אודהליה ברלין'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube: No definitive match found.

🎼 (14) Processing Row 36: 'תחשוב טוב' by 'אודי דוידי'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=VImbgW6ZCxk

🎼 (15) Processing Row 37: 'ים של גיבורים' by 'אודיה'
   🔍 Searching Spotify...
   🎵 Spotify: No definitive match found.
   🔍 Searching YouTube...
   📺 YouTube: No definitive match found.

🎼 (16) Processing Row 38: 'השנה החדשה שלי' by 'אוהד חיטמן'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=e0ABJEzPiYM

🎼 (17) Processing Row 39: 'בכה כינור' by 'אוריאל שלומי'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=wvQlMT9H2jU

🎼 (18) Processing Row 40: 'בלדה לשוטר' by 'אושיק לוי'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=HP0iT4v-pDU

🎼 (19) Processing Row 41: 'נגעת לי בלב' by 'אייל גולן'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=bzZtDkMueUA

🎼 (20) Processing Row 42: 'ימים טובים' by 'אייל גולן'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=b5W7TBcnJq4

🎼 (21) Processing Row 43: 'את לי הנצח' by 'אייל גולן'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=GdHWe14VBYo

🎼 (22) Processing Row 44: 'אייל גולן קורא לך Eyal Golan' by 'אייל גולן'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=iYUuus21OEs

🎼 (23) Processing Row 45: 'השיר שיביא לך אהבה' by 'אייל גולן'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube: No definitive match found.

🎼 (24) Processing Row 46: 'תבואי היום' by 'אייל גולן'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=3VT3VIRQPKA

🎼 (25) Processing Row 47: 'לא יכולתי לעשות כלום' by 'אילן וירצברג ושמעון גלבץ'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=AUOu-CSXYr0

🎼 (26) Processing Row 48: 'בשנה הבאה' by 'אילנית'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=n3AAzk3UAws

🎼 (27) Processing Row 49: 'אי שם' by 'אילנית'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=tl5PpPzYcAA

🎼 (28) Processing Row 50: 'שיר של יום חולין' by 'אילנית'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=_Sx3he4ABw0

🎼 (29) Processing Row 51: 'ארץ' by 'אילנית'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=D3l8vnfbnPs

🎼 (30) Processing Row 52: 'נחמה' by 'אילנית'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=UuozN7b357w

🎼 (31) Processing Row 53: 'ללכת שבי אחריך' by 'אילנית'
   🔍 Searching Spotify...
   🎵 Spotify: No definitive match found.
   🔍 Searching YouTube...
   📺 YouTube (High Probability Match - Alternative): https://www.youtube.com/watch?v=3Fz56kP65_0

🎼 (32) Processing Row 54: 'שמח בני בחלקך' by 'איציק אשל'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=UeaZFZfvbV4

🎼 (33) Processing Row 55: 'אני העבד' by 'איציק קלה'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=-HLgXxl22ks

🎼 (34) Processing Row 56: 'מאמי מאמי' by 'איציק קלה'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=FfOImMyH8yg

🎼 (35) Processing Row 57: 'ישמח חתני' by 'איציק קלה'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=K7JEezNO6qg

🎼 (36) Processing Row 58: 'בגלל הרוח' by 'איתי לוי'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=I9WynOT3aBY

🎼 (37) Processing Row 59: 'אין לי מקום אחר' by 'איתי לוי'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=RAsTZqalx-g

🎼 (38) Processing Row 60: 'אלוהים נתן לך במתנה' by 'איתן מסורי'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=b7AGXZ-UhWk

🎼 (39) Processing Row 61: 'זמן פרידה' by 'אלה לי'
   🔍 Searching Spotify...
   🎵 Spotify: No definitive match found.
   🔍 Searching YouTube...
   📺 YouTube: No definitive match found.

🎼 (40) Processing Row 62: 'בא לשכונה בחור חדש' by 'אלון אולארצ'יק'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=Ac33hnCIFvE

🎼 (41) Processing Row 63: 'שיר לאמא' by 'אלון עדר ולהקה'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=Ovfet4GP9y0

🎼 (42) Processing Row 64: 'הנשמה' by 'אלי לוזון'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=T3pr4tpHyGk

🎼 (43) Processing Row 65: 'אור' by 'אליעד נחום'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=O21OZkP8anw

🎼 (44) Processing Row 66: 'פרדס רימונים' by 'אליעזר בוצר'
   🔍 Searching Spotify...
   🎵 Spotify: No definitive match found.
   🔍 Searching YouTube...
   📺 YouTube: No definitive match found.

🎼 (45) Processing Row 67: 'צמאה' by 'אליעזר בוצר'
   🔍 Searching Spotify...
   🎵 Spotify: No definitive match found.
   🔍 Searching YouTube...
   📺 YouTube: No definitive match found.

🎼 (46) Processing Row 68: 'מישהו לדבר איתו' by 'אלמוג טבקה ואתי רומנו'
   🔍 Searching Spotify...
   🎵 Spotify: No definitive match found.
   🔍 Searching YouTube...
   📺 YouTube: Not Found.

🎼 (47) Processing Row 69: 'ילדים של החיים' by 'אמיר דדון'
   🔍 Searching Spotify...
   🎵 Spotify: No definitive match found.
   🔍 Searching YouTube...
   📺 YouTube: No definitive match found.

🎼 (48) Processing Row 70: 'אור גדול' by 'אמיר דדון'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=jeU9Sbq0D0A

🎼 (49) Processing Row 71: 'שום דבר' by 'אמיר דדון'
   🔍 Searching Spotify...
   🎵 Spotify: No definitive match found.
   🔍 Searching YouTube...
   📺 YouTube: No definitive match found.

🎼 (50) Processing Row 72: 'לבחור נכון' by 'אמיר דדון'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=yjJcnqZqciU

🎼 (51) Processing Row 73: 'קטן עלינו' by 'אמני ישראל'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=kB0_vTznm_8

🎼 (52) Processing Row 74: 'שבט אחים ואחיות' by 'אמנים שונים'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=xWx3R7WaAQY

🎼 (53) Processing Row 75: 'בראשית' by 'אסף אמדורסקי'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=O4d2MpuszZ4

🎼 (54) Processing Row 76: 'חלמי חלום' by 'אסתר עופרים'
   🔍 Searching Spotify...
   🎵 Spotify: No definitive match found.
   🔍 Searching YouTube...
   📺 YouTube: No definitive match found.

🎼 (55) Processing Row 77: 'שכב בני' by 'אסתר עופרים'
   🔍 Searching Spotify...
   🎵 Spotify: No definitive match found.
   🔍 Searching YouTube...
   📺 YouTube: No definitive match found.

🎼 (56) Processing Row 78: 'היו לילות' by 'אסתר עופרים'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=neZHpWExqwQ

🎼 (57) Processing Row 79: 'שיר הנודד' by 'אסתר עופרים'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=QWQLxNBHXQg

🎼 (58) Processing Row 80: 'חץ בתוך הלב' by 'אסתר שמיר'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=nudApz-p74I

🎼 (59) Processing Row 81: 'לראות את האור' by 'אפרת גוש'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=7UAnc7lqJjM

🎼 (60) Processing Row 82: 'חדר משלי' by 'אקרדי דוכין'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=_ouCTRQTCeU

🎼 (61) Processing Row 83: 'אנה אפנה' by 'ארז לב ארי'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=fTRm3nyNpro

🎼 (62) Processing Row 84: 'רקפות בין הסלעים' by 'אריאל הורוביץ'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube: No definitive match found.

🎼 (63) Processing Row 85: 'נחל איתן' by 'אריאל הורוביץ'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=BnHTnCdRRG0

🎼 (64) Processing Row 86: 'ואיך שלא' by 'אריאל זילבר'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=2GxJ_E4Alsw

🎼 (65) Processing Row 87: 'ברוש' by 'אריאל זילבר'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=xd9W-rBp7q4

🎼 (66) Processing Row 88: 'סיגל' by 'אריס סאן'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=yn8Q6PLWQQs

🎼 (67) Processing Row 89: 'תל אביב' by 'אריס סאן'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=GSPayOF4-CI

🎼 (68) Processing Row 90: 'בחיים הכל עובר' by 'אריס סאן'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=MZBFVK8CpE8

🎼 (69) Processing Row 91: 'דם דם' by 'אריס סאן'
   🔍 Searching Spotify...
   🎵 Spotify: No definitive match found.
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=AIoJTXQTXEo

🎼 (70) Processing Row 92: 'שלום חבר' by 'אריק איינשטיין'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=pXCTQyHNYyI

🎼 (71) Processing Row 93: 'עטור מצחך' by 'אריק איינשטיין'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=wcayUsa9yvw

🎼 (72) Processing Row 94: 'גיטרה וכינור' by 'אריק איינשטיין'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=6UltSHD_BbM

🎼 (73) Processing Row 95: 'למה לי לקחת ללב' by 'אריק איינשטיין'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=PIkk1eGFplc

🎼 (74) Processing Row 96: 'שלח לי שקט' by 'אריק איינשטיין'
   🔍 Searching Spotify...
   🎵 Spotify: No definitive match found.
   🔍 Searching YouTube...
   📺 YouTube: No definitive match found.

🎼 (75) Processing Row 97: 'אני ואתה' by 'אריק איינשטיין'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=gP6PS-poyMg

🎼 (76) Processing Row 98: 'צא מזה' by 'אריק איינשטיין'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=2GRq0Wia9PQ

🎼 (77) Processing Row 99: 'עוף גוזל' by 'אריק איינשטיין'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=kxDBpbMDsZA

🎼 (78) Processing Row 100: 'האור בקצה' by 'אריק איינשטיין'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=f-cD0MxpMH0

🎼 (79) Processing Row 101: 'הכניסיני תחת כנפך' by 'אריק איינשטיין'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=KmZ2H11cBu0

🎼 (80) Processing Row 102: 'פסק זמן' by 'אריק איינשטיין'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=Uw4zU-fHpx0

🎼 (81) Processing Row 103: 'מכופף הבננות' by 'אריק איינשטיין'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube: No definitive match found.

🎼 (82) Processing Row 104: 'גברת עם סלים' by 'אריק איינשטיין'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=2LhX65c4qEU

🎼 (83) Processing Row 105: 'שיר העמק' by 'אריק איינשטיין'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=Tbs8VFNdFpU

🎼 (84) Processing Row 106: 'לפעמים אני עצוב ולפעמים שמח' by 'אריק איינשטיין'
   🔍 Searching Spotify...
   🎵 Spotify: No definitive match found.
   🔍 Searching YouTube...
   📺 YouTube: No definitive match found.

🎼 (85) Processing Row 107: 'מכופף הבננות' by 'אריק איינשטיין'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube: No definitive match found.

🎼 (86) Processing Row 108: 'ברלה צא' by 'אריק איינשטיין'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=CyKvBfbfA14

🎼 (87) Processing Row 109: 'כמה טוב שבאת הביתה' by 'אריק איינשטיין'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=Che2jea8z_Q

🎼 (88) Processing Row 110: 'שיר של אחרי מלחמה' by 'אריק איינשטיין'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=R0O4ZFgRLWA

🎼 (89) Processing Row 111: 'לילה לילה' by 'אריק איינשטיין'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=SIdljPIHYr8

🎼 (90) Processing Row 112: 'ואולי' by 'אריק איינשטיין'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=Vv-Nrl724Zg

🎼 (91) Processing Row 113: 'יש בי אהבה' by 'אריק איינשטיין'
   ✅ Spotify link already exists
   🔍 Searching YouTube...
   📺 YouTube (Exact Match): https://www.youtube.com/watch?v=5WEggKymynE

"""


# --- Script Logic ---

def parse_log_text(text):
    """
    Parses the log text to extract row numbers and YouTube links.
    Returns a dictionary where keys are row numbers and values are YouTube links.
    """
    data = {}
    # Regex to capture the row number and the YouTube link
    # It handles both http://googleusercontent.com/youtube.com/ and standard YouTube links
    # and optional 'https://www.'
    pattern = re.compile(
        r"Processing Row (\d+):.*?"  # Capture row number
        r"📺 YouTube \(Exact Match\): (https?://(?:www\.)?(?:googleusercontent\.com/)?youtube\.com/[^\s]+)",
        # Capture URL
        re.DOTALL  # Allows . to match newlines
    )

    matches = pattern.finditer(text)

    for match in matches:
        row_num = int(match.group(1))
        youtube_link = match.group(2)
        data[row_num] = youtube_link

    return data


def update_google_sheet(data_to_update, spreadsheet_id, worksheet_name, creds_file):
    """
    Connects to Google Sheets and updates column E with YouTube links
    based on the row numbers.
    """
    try:
        # Authenticate with Google
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
        client = gspread.authorize(creds)

        # Open the spreadsheet and select the worksheet
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet(worksheet_name)
        print(f"Successfully connected to worksheet '{worksheet_name}'")

        # Create a list of update operations
        updates = []
        for row_num, link in data_to_update.items():
            # gspread uses 1-based indexing for rows and columns
            # Column 'E' is the 5th column
            updates.append({
                'range': f'E{row_num}',
                'values': [[link]]
            })
            print(f"Prepared to update Row {row_num}, Column E with: {link}")

        if updates:
            # Batch update the cells
            worksheet.batch_update(updates)
            print("Successfully updated the Google Sheet.")
        else:
            print("No YouTube links found to update.")

    except gspread.exceptions.SpreadsheetNotFound:
        print(f"Error: Spreadsheet with ID '{spreadsheet_id}' not found. Check the ID.")
    except gspread.exceptions.NoWorksheetFound:
        print(f"Error: Worksheet with name '{worksheet_name}' not found. Check the worksheet name.")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    extracted_data = parse_log_text(log_text)

    if extracted_data:
        print("\n--- Extracted Data ---")
        for row, link in extracted_data.items():
            print(f"Row {row}: {link}")

        print("\n--- Updating Google Sheet ---")
        update_google_sheet(extracted_data, SPREADSHEET_ID, WORKSHEET_NAME, CREDS_FILE)
    else:
        print("No data extracted from the log text. Check the input format or regex pattern.")