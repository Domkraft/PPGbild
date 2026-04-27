import requests
from bs4 import BeautifulSoup
import re
import os
from PIL import Image, ImageDraw
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
    
    # Regex som fångar: Rank, Lag, Matcher och Poäng
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
    """Skapar visualiseringen med korrekt transparens och stapling."""
    if not teams:
        return False

    # Inställningar för bilden
    width, height = 1200, 600
    logo_size = 90
    margin = 120
    
    # Skapa en canvas med vit bakgrund (RGBA för att kunna arbeta med lager)
    img = Image.new('RGBA', (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    min_ppm = min(t['ppm'] for t in teams)
    max_ppm = max(t['ppm'] for t in teams)
    ppm_range = max_ppm - min_ppm if max_ppm != min_ppm else 1

    # Sortering: Lägst PPM först. 
    # Vid lika PPM: Högst rank (störst siffra) först så att bäst lag ritas sist (överst).
    teams.sort(key=lambda x: (x['ppm'], -x['rank']))
    
    ppm_slots = {}

    for team in teams:
        # Beräkna X-position
        x_ratio = (team['ppm'] - min_ppm) / ppm_range
        x_pos = int(margin + x_ratio * (width - 2 * margin))
        
        # Beräkna Y-position (stapling vid samma PPM)
        slot_key = round(team['ppm'], 2)
        count = ppm_slots.get(slot_key, 0)
        y_pos = height - 160 - (count * (logo_size + 5))
        ppm_slots[slot_key] = count + 1
        
        # Sök efter logotyp (testar både mellanslag och understreck)
        possible_fnames = [f"logos/{team['name']}.png", f"logos/{team['name'].replace(' ', '_')}.png"]
        logo_found = False

        for fname in possible_fnames:
            if os.path.exists(fname):
                try:
                    logo = Image.open(fname).convert("RGBA")
                    # Skala om med bibehållen aspekt och hög kvalitet
                    logo.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
                    
                    # Centrera logotypen på koordinaten
                    paste_x = x_pos - logo.width // 2
                    paste_y = y_pos - logo.height // 2
                    
                    # Klistra in med logotypen själv som mask (viktigt för transparens!)
                    img.paste(logo, (paste_x, paste_y), logo)
                    logo_found = True
                    break
                except Exception as e:
                    print(f"Fel vid bearbetning av {fname}: {e}")

        if not logo_found:
            # Om bild saknas, skriv text istället
            draw.text((x_pos, y_pos), team['name'], fill="black")

    # Rita axeln
    draw.line((margin, height - 100, width - margin, height - 100), fill="black", width=3)
    
    # Etiketter för PPM
    draw.text((margin, height - 85), f"{min_ppm:.2f} PPM", fill="black")
    draw.text((width - margin - 60, height - 85), f"{max_ppm:.2f} PPM", fill="black")
    
    # Spara som JPEG för optimal storlek på Bluesky
    img.convert("RGB").save("allsvenskan_ppm.jpg", "JPEG", quality=95)
    return True

def post_to_bluesky():
    """Hanterar inloggning och publicering på Bluesky."""
    handle = os.environ.get('BSKY_HANDLE')
    password = os.environ.get('BSKY_PASSWORD')
    
    if not handle or not password:
        print("Inloggningsuppgifter saknas i miljövariabler.")
        return

    try:
        client = Client()
        client.login(handle, password)
        
        with open("allsvenskan_ppm.jpg", "rb") as f:
            img_data = f.read()
            
        client.send_image(
            text="Dagens Allsvenska tabell baserat på Poäng Per Match (PPM). \n\n#Allsvenskan #PPM #SvenskFotboll",
            image=img_data,
            image_alt="PPM-karta över Allsvenskan"
        )
        print("Publicerat på Bluesky!")
    except Exception as e:
        print(f"Kunde inte posta till Bluesky: {e}")

if __name__ == "__main__":
    print("Skriptet startar...")
    data = get_table_data()
    if data:
        print(f"Data hämtad för {len(data)} lag.")
        if create_visual(data):
            print("Bild genererad framgångsrikt.")
            post_to_bluesky()
    else:
        print("Kunde inte hitta någon tabell-data.")
