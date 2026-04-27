import requests
from bs4 import BeautifulSoup
import re
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from atproto import Client

def get_table_data():
    """Hämtar tabelluppgifter från SVT Text sida 343."""
    url = "https://www.svt.se/text-tv/webb/343"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Kunde inte hämta data från SVT: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    text = soup.get_text()
    
    pattern = re.compile(r"^\s*(\d+)\s+([A-ZÅÄÖ][a-zåäöA-ZÅÄÖ0-9\s\-\.]+?)\s+(\d+)\s+\d+\s+\d+\s+\d+\s+[\d\-]+\s+(\d+)", re.MULTILINE)
    
    teams = []
    for match in pattern.finditer(text):
        rank = int(match.group(1))
        name = match.group(2).strip()
        games = int(match.group(3))
        points = int(match.group(4))
        
        if games > 0:
            ppm = points / games
            teams.append({'rank': rank, 'name': name, 'ppm': ppm})
    
    return teams

def create_visual(teams):
    """Skapar visualiseringen med rubriker, flerradig tidstämpel och PPM-axeln."""
    if not teams:
        return False

    width, height = 1200, 750 # Lite mer höjd för att rymma flerradig tidstämpel
    logo_size = 90
    margin = 120
    
    img = Image.new('RGBA', (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    try:
        font_main = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 45)
        font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
        font_time = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except:
        font_main = font_sub = font_time = ImageFont.load_default()

    # --- RUBRIKER (Vänster) ---
    draw.text((40, 40), "Allsvenskan", fill="black", font=font_main)
    draw.text((40, 95), "relativ position (poäng per match)", fill=(80, 80, 80), font=font_sub)
    
    # --- TIDSTÄMPEL (Höger, tre rader) ---
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    
    # Vi högerjusterar genom att dra bort ett uppskattat värde från högerkanten
    r_margin = width - 180
    draw.text((r_margin, 40), "Uppdaterad:", fill=(120, 120, 120), font=font_time)
    draw.text((r_margin, 65), date_str, fill=(120, 120, 120), font=font_time)
    draw.text((r_margin, 90), time_str, fill=(120, 120, 120), font=font_time)

    # --- DIAGRAM-LOGIK ---
    min_ppm = min(t['ppm'] for t in teams)
    max_ppm = max(t['ppm'] for t in teams)
    ppm_range = max_ppm - min_ppm if max_ppm != min_ppm else 1

    # Sortera för korrekt stapling
    teams.sort(key=lambda x: (x['ppm'], -x['rank']))
    ppm_slots = {}

    for team in teams:
        x_ratio = (team['ppm'] - min_ppm) / ppm_range
        x_pos = int(margin + x_ratio * (width - 2 * margin))
        
        slot_key = round(team['ppm'], 2)
        count = ppm_slots.get(slot_key, 0)
        
        # MINSKAT AVSTÅND: Ändrat från logo_size + 5 till logo_size * 0.7 
        # Detta gör att de överlappar snyggt vertikalt
        y_pos = height - 180 - (count * (logo_size * 0.75))
        ppm_slots[slot_key] = count + 1
        
        possible_fnames = [f"logos/{team['name']}.png", f"logos/{team['name'].replace(' ', '_')}.png"]
        logo_found = False

        for fname in possible_fnames:
            if os.path.exists(fname):
                try:
                    logo = Image.open(fname).convert("RGBA")
                    logo.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
                    img.paste(logo, (x_pos - logo.width // 2, int(y_pos) - logo.height // 2), logo)
                    logo_found = True
                    break
                except:
                    continue

        if not logo_found:
            draw.text((x_pos, int(y_pos)), team['name'], fill="black")

    # Rita axeln
    draw.line((margin, height - 120, width - margin, height - 120), fill="black", width=3)
    
    # Etiketter för PPM
    draw.text((margin, height - 100), f"{min_ppm:.2f} PPM", fill="black", font=font_sub)
    draw.text((width - margin - 80, height - 100), f"{max_ppm:.2f} PPM", fill="black", font=font_sub)
    
    img.convert("RGB").save("allsvenskan_ppm.jpg", "JPEG", quality=95)
    return True

def post_to_bluesky():
    handle = os.environ.get('BSKY_HANDLE')
    password = os.environ.get('BSKY_PASSWORD')
    if not handle or not password: return

    try:
        client = Client()
        client.login(handle, password)
        with open("allsvenskan_ppm.jpg", "rb") as f:
            img_data = f.read()
        client.send_image(
            text=f"Allsvenskan PPM-uppdatering {datetime.now().strftime('%Y-%m-%d')}. #Allsvenskan #PPM",
            image=img_data,
            image_alt="Aktuell tabell baserat på poäng per match."
        )
        print("Postad på Bluesky!")
    except Exception as e:
        print(f"Bluesky-fel: {e}")

if __name__ == "__main__":
    data = get_table_data()
    if data:
        if create_visual(data):
            post_to_bluesky()
