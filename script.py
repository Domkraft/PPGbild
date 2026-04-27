import requests
from bs4 import BeautifulSoup
import re
import os
from PIL import Image, ImageDraw, ImageOps
from atproto import Client

def remove_white_background(img):
    """Gör vita pixlar i en bild genomskinliga."""
    img = img.convert("RGBA")
    datas = img.getdata()

    new_data = []
    for item in datas:
        # Känner av pixlar som är mycket nära vita (tröskelvärde 240 av 255)
        if item[0] > 235 and item[1] > 235 and item[2] > 235:
            new_data.append((255, 255, 255, 0))  # Gör pixeln helt genomskinlig
        else:
            new_data.append(item)

    img.putdata(new_data)
    return img

def get_table_data():
    url = "https://www.svt.se/text-tv/webb/343"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Kunde inte hämta data: {e}")
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
            teams.append({'rank': rank, 'name': name, 'ppm': points / games})
    return teams

def create_visual(teams):
    if not teams: return False

    width, height = 1200, 600
    logo_size = 90 # Något större för tydlighet
    margin = 120
    
    # Skapa bild med RGBA för att hantera transparens korrekt under komposition
    img = Image.new('RGBA', (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    min_ppm = min(t['ppm'] for t in teams)
    max_ppm = max(t['ppm'] for t in teams)
    ppm_range = max_ppm - min_ppm if max_ppm != min_ppm else 1

    # Sortera för korrekt stapling (bäst placerade lag hamnar överst)
    teams.sort(key=lambda x: (x['ppm'], -x['rank']))
    
    ppm_slots = {}

    for team in teams:
        x_ratio = (team['ppm'] - min_ppm) / ppm_range
        x_pos = int(margin + x_ratio * (width - 2 * margin))
        
        slot_key = round(team['ppm'], 2)
        count = ppm_slots.get(slot_key, 0)
        y_pos = height - 150 - (count * (logo_size - 10)) # Lite överlapp vertikalt ser ofta bra ut
        ppm_slots[slot_key] = count + 1
        
        possible_filenames = [f"logos/{team['name']}.png", f"logos/{team['name'].replace(' ', '_')}.png"]
        
        logo_found = False
        for fname in possible_filenames:
            if os.path.exists(fname):
                try:
                    logo = Image.open(fname).convert("RGBA")
                    
                    # Kör funktionen som tar bort vit bakgrund
                    logo = remove_white_background(logo)
                    
                    logo.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
                    img.paste(logo, (x_pos - logo.width // 2, y_pos - logo.height // 2), logo)
                    logo_found = True
                    break
                except Exception as e:
                    print(f"Fel vid logotyp {fname}: {e}")

        if not logo_found:
            draw.text((x_pos, y_pos), team['name'], fill="black")

    # Rita axeln
    draw.line((margin, height - 100, width - margin, height - 100), fill="black", width=3)
    draw.text((margin, height - 85), f"{min_ppm:.2f} PPM (Botten)", fill="black")
    draw.text((width - margin - 60, height - 85), f"{max_ppm:.2f} PPM (Toppen)", fill="black")
    
    # Spara som högkvalitativ JPEG (Bluesky hanterar detta bra)
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
            text="Aktuell PPM-karta för Allsvenskan. Lag placerade efter effektivitet (poäng/match). \n\n#Allsvenskan #PPM",
            image=img_data,
            image_alt="Visualisering av Allsvenskans tabell baserat på poäng per match."
        )
        print("Postad!")
    except Exception as e:
        print(f"Bluesky-fel: {e}")

if __name__ == "__main__":
    data = get_table_data()
    if data:
        if create_visual(data):
            post_to_bluesky()
