import requests
from bs4 import BeautifulSoup
import re
import os
from PIL import Image, ImageDraw
from atproto import Client

def get_table_data():
    """Hämtar och parsar data från SVT Text sida 343."""
    url = "https://www.svt.se/text-tv/webb/343"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Kunde inte hämta data från SVT: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    text = soup.get_text()
    
    # Regex för att hitta: Rank, Lag, Matcher, V, O, F, Mål, Poäng
    # Justerad för att hantera lagnamn med mellanslag och siffror
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
    """Skapar PPM-visualiseringen."""
    if not teams:
        return False

    # Inställningar för bilden
    width, height = 1200, 600
    logo_size = 80
    margin = 120
    bg_color = (255, 255, 255) # Vit
    
    img = Image.new('RGBA', (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Beräkna omfång för axeln
    min_ppm = min(t['ppm'] for t in teams)
    max_ppm = max(t['ppm'] for t in teams)
    ppm_range = max_ppm - min_ppm if max_ppm != min_ppm else 1

    # Sortera: Lägst PPM först. Vid lika PPM: Högst rank (störst siffra) först 
    # så att de med lägre rank (bättre placering) ritas sist/överst.
    teams.sort(key=lambda x: (x['ppm'], -x['rank']))
    
    # Håll koll på stapling för överlappande PPM
    ppm_slots = {}

    for team in teams:
        # X-position baserat på PPM
        x_ratio = (team['ppm'] - min_ppm) / ppm_range
        x_pos = int(margin + x_ratio * (width - 2 * margin))
        
        # Y-position (stapling)
        slot_key = round(team['ppm'], 2)
        count = ppm_slots.get(slot_key, 0)
        y_pos = height - 150 - (count * (logo_size + 10))
        ppm_slots[slot_key] = count + 1
        
        # Försök ladda logotypen
        # Vi testar både med mellanslag och understreck för att vara säkra
        possible_filenames = [
            f"logos/{team['name']}.png",
            f"logos/{team['name'].replace(' ', '_')}.png"
        ]
        
        logo_found = False
        for fname in possible_filenames:
            if os.path.exists(fname):
                try:
                    logo = Image.open(fname).convert("RGBA")
                    logo.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
                    # Centrera logon på x-koordinaten
                    img.paste(logo, (x_pos - logo.width // 2, y_pos - logo.height // 2), logo)
                    logo_found = True
                    break
                except Exception as e:
                    print(f"Fel vid laddning av {fname}: {e}")

        if not logo_found:
            # Reserv om bild saknas: Skriv ut namnet
            draw.text((x_pos, y_pos), team['name'], fill="black")

    # Rita axeln
    draw.line((margin, height - 100, width - margin, height - 100), fill="black", width=3)
    
    # Lägg till labels för min/max PPM
    draw.text((margin, height - 80), f"{min_ppm:.2f} PPM", fill="black")
    draw.text((width - margin - 40, height - 80), f"{max_ppm:.2f} PPM", fill="black")
    
    img.convert("RGB").save("allsvenskan_ppm.jpg", "JPEG", quality=95)
    return True

def post_to_bluesky():
    """Postar den genererade bilden till Bluesky."""
    handle = os.environ.get('BSKY_HANDLE')
    password = os.environ.get('BSKY_PASSWORD')
    
    if not handle or not password:
        print("Fel: Saknar inloggningsuppgifter för Bluesky.")
        return

    try:
        client = Client()
        client.login(handle, password)
        
        with open("allsvenskan_ppm.jpg", "rb") as f:
            img_data = f.read()
            
        client.send_image(
            text="Aktuell ställning i Allsvenskan baserat på Poäng Per Match (PPM). \n\n#Allsvenskan #SvenskFotboll",
            image=img_data,
            image_alt="Diagram över Allsvenskans lag placerade efter poäng per match."
        )
        print("Inlägget publicerat på Bluesky!")
    except Exception as e:
        print(f"Kunde inte posta till Bluesky: {e}")

if __name__ == "__main__":
    print("Startar skript...")
    table_data = get_table_data()
    if table_data:
        print(f"Hämtade data för {len(table_data)} lag.")
        if create_visual(table_data):
            print("Bild genererad.")
            post_to_bluesky()
    else:
        print("Ingen data hittades.")
