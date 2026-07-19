import requests
from bs4 import BeautifulSoup
import re
import os
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from atproto import Client, client_utils

def check_if_games_played():
    """Kollar sida 344 om det spelats matcher idag."""
    url = "https://www.svt.se/text-tv/webb/344"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text()
        
        months = ["jan", "feb", "mar", "apr", "maj", "jun", "jul", "aug", "sep", "okt", "nov", "dec"]
        now = datetime.utcnow() + timedelta(hours=2)
        today_str = f"{now.day} {months[now.month-1]}"
        
        if today_str in text.lower():
            print(f"Matcher hittade för {today_str}. Går vidare till postning.")
            return True
        else:
            print(f"Inga matcher spelade idag ({today_str}). Avbryter.")
            return False
    except Exception as e:
        print(f"Kunde inte kolla spelschema: {e}")
        return True

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
    width, height = 1200, 750
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

    draw.text((40, 40), "Allsvenskan", fill="black", font=font_main)
    draw.text((40, 95), "relativ position (poäng per match)", fill=(80, 80, 80), font=font_sub)
    
    now = datetime.utcnow() + timedelta(hours=2)
    r_margin = width - 180
    draw.text((r_margin, 40), "Uppdaterad:", fill=(120, 120, 120), font=font_time)
    draw.text((r_margin, 65), now.strftime("%Y-%m-%d"), fill=(120, 120, 120), font=font_time)
    draw.text((r_margin, 90), now.strftime("%H:%M"), fill=(120, 120, 120), font=font_time)

    min_ppm = min(t['ppm'] for t in teams)
    max_ppm = max(t['ppm'] for t in teams)
    ppm_range = max_ppm - min_ppm if max_ppm != min_ppm else 1
    
    teams.sort(key=lambda x: (x['ppm'], -x['rank']))
    ppm_slots = {}

    for team in teams:
        # HÄR ÄR ÄNDRINGEN: X-positionen beräknas på den exakta, oavrundade PPM-nivån
        x_ratio = (team['ppm'] - min_ppm) / ppm_range
        x_pos = int(margin + x_ratio * (width - 2 * margin))
        
        # Vi avrundar fortfarande till 2 decimaler ENBART för att gruppera Y-axeln (staplingen)
        slot_key = round(team['ppm'], 2)
        count = ppm_slots.get(slot_key, 0)
        y_pos = height - 180 - (count * (logo_size * 0.75))
        ppm_slots[slot_key] = count + 1
        
        possible_fnames = [f"logos/{team['name']}.png", f"logos/{team['name'].replace(' ', '_')}.png"]
        logo_found = False
        for fname in possible_fnames:
            if os.path.exists(fname):
                try:
                    logo = Image.open(fname).convert("RGBA")
                    logo.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
                    # Skölden centreras nu på sin exakta unika x_pos, men behåller sin staplade y_pos
                    img.paste(logo, (x_pos - logo.width // 2, int(y_pos) - logo.height // 2), logo)
                    logo_found = True
                    break
                except: continue
        if not logo_found:
            draw.text((x_pos, int(y_pos)), team['name'], fill="black")

    draw.line((margin, height - 120, width - margin, height - 120), fill="black", width=3)
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
        sweden_time = datetime.utcnow() + timedelta(hours=2)
        text_builder = client_utils.TextBuilder()
        text_builder.text(f"Allsvenskan PPM-uppdatering {sweden_time.strftime('%Y-%m-%d %H:%M')}\n\n")
        tags = [("#Allsvenskan", "Allsvenskan"), ("#ifkgbg", "ifkgbg"), ("#AIK", "AIK"), ("#MFF", "MFF"), 
                ("#HIF", "HIF"), ("#DIF", "DIF"), ("#GAIS", "GAIS"), ("#ÖIS", "ÖIS")]
        for tag, label in tags:
            text_builder.tag(tag, label)
            text_builder.text(" ")
        client.send_image(text=text_builder, image=img_data, image_alt="PPM-karta")
    except Exception as e:
        print(f"Fel: {e}")

if __name__ == "__main__":
    if check_if_games_played():
        table_data = get_table_data()
        if table_data:
            if create_visual(table_data):
                post_to_bluesky()
