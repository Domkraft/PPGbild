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
    """Skapar visualiseringen med rubriker, tidstämpel och PPM-axeln."""
    if not teams:
        return False

    # Inställningar för bilden
    width, height = 1200, 700 # Ökad höjd för att få plats med rubrik
    logo_size = 90
    margin = 120
    
    img = Image.new('RGBA', (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Försök ladda en font, annars använd standard
    try:
        # GitHub Actions körs på Ubuntu, så vi letar efter en vanlig linux-font
        font_main = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
        font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        font_time = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except:
        font_main = font_sub = font_time = ImageFont.load_default()

    # --- TEXTER I ÖVRE DELEN ---
    
    # Övre vänstra hörnet: Rubrik
    draw.text((40, 30), "Allsvenskan", fill="black", font=font_main)
    draw.text((40, 80), "relativ position (poäng per match)", fill=(100, 100, 100), font=font_sub)
    
    # Övre högra hörnet: Datum och klockslag
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    draw.text((width - 200, 30), f"Uppdaterad: {now}", fill=(120, 120, 120), font=font_time)

    # --- DIAGRAM-LOGIK ---

    min_ppm = min(t['ppm'] for t in teams)
    max_ppm = max(t['ppm'] for t in teams)
    ppm_range = max_ppm - min_ppm if max_ppm != min_ppm else 1

    teams.sort(key=lambda x: (x['ppm'], -x['rank']))
    ppm_slots = {}

    for team in teams:
        x_ratio = (team['ppm'] - min_ppm) / ppm_range
        x_pos = int(margin + x_ratio * (width - 2 * margin))
        
        slot_key = round(team['ppm'], 2)
        count = ppm_slots.get(slot_key, 0)
        # Justerad y_pos för att börja lägre ner pga rubriken
        y_pos = height - 180 - (count * (logo_size + 5))
        ppm_slots[slot_key] = count + 1
        
        possible_fnames = [f"logos/{team['name']}.png", f"logos/{team['name'].replace(' ', '_')}.png"]
        logo_found = False

        for fname in possible_fnames:
            if os.path.exists(fname):
                try:
                    logo = Image.open(fname).convert("RGBA")
                    logo.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
                    paste_x = x_pos - logo.width // 2
                    paste_y = y_pos - logo.height // 2
                    img.paste(logo, (paste_x, paste_y), logo)
                    logo_found = True
                    break
                except:
                    continue

        if not logo_found:
            draw.text((x_pos, y_pos), team['name'], fill="black")

    # Rita axeln
    draw.line((margin, height - 120, width - margin, height - 120), fill="black", width=3)
    
    # Etiketter för PPM på axeln
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
            text=f"Aktuell ställning i Allsvenskan (PPM) {datetime.now().strftime('%Y-%m-%d')}. #Allsvenskan #PPM",
            image=img_data,
            image_alt="PPM-karta över Allsvenskan"
        )
        print("Publicerat på Bluesky!")
    except Exception as e:
        print(f"Kunde inte posta: {e}")

if __name__ == "__main__":
    table_data = get_table_data()
    if table_data:
        if create_visual(table_data):
            post_to_bluesky()
