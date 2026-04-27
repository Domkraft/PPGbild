import requests
from bs4 import BeautifulSoup
import re
from PIL import Image, ImageDraw
from atproto import Client

# 1. Hämta data från SVT Text
def get_table():
    url = "https://www.svt.se/text-tv/webb/343"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    text = soup.get_text()
    
    # Regex för att hitta rader: Placering, Lag, Matcher, V, O, F, Mål, Poäng
    # Exempel: " 1 Malmö FF      4  4  0  0  12-1   12"
    pattern = re.compile(r"(\d+)\s+([A-Za-zÅÄÖåäö\s\-]+?)\s+(\d+)\s+\d+\s+\d+\s+\d+\s+[\d\-]+\s+(\d+)")
    teams = []
    for match in pattern.finditer(text):
        rank, name, games, points = match.groups()
        name = name.strip()
        ppm = int(points) / int(games)
        teams.append({'rank': int(rank), 'name': name, 'ppm': ppm})
    return teams

# 2. Skapa bilden
def create_chart(teams):
    width, height = 1200, 400
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    min_ppm = min(t['ppm'] for t in teams)
    max_ppm = max(t['ppm'] for t in teams)
    
    # Skalningsfunktion
    def get_x(ppm):
        if max_ppm == min_ppm: return width // 2
        return 100 + (ppm - min_ppm) / (max_ppm - min_ppm) * (width - 200)

    # Sortera för att hantera stapling (lägst rank överst vid samma PPM)
    teams.sort(key=lambda x: (x['ppm'], -x['rank']))
    
    ppm_counts = {}
    logo_size = 60
    
    for team in teams:
        x = int(get_x(team['ppm']))
        count = ppm_counts.get(team['ppm'], 0)
        y = height - 100 - (count * (logo_size + 5))
        ppm_counts[team['ppm']] = count + 1
        
        try:
            logo = Image.open(f"logos/{team['name'].replace(' ', '_')}.png").convert("RGBA")
            logo = logo.resize((logo_size, logo_size))
            img.paste(logo, (x - logo_size//2, y), logo)
        except FileNotFoundError:
            draw.text((x, y), team['name'], fill="black")

    # Rita axel
    draw.line((100, height-80, width-100, height-80), fill="black", width=2)
    img.save("daily_table.png")

# 3. Posta till Bluesky
def post_to_bluesky():
    client = Client()
    client.login('ditt-konto.bsky.social', 'ditt-app-lösenord')
    with open('daily_table.png', 'rb') as f:
        img_data = f.read()
    client.send_image(text="Dagens Allsvenska PPM-karta", image=img_data, image_alt="Tabellvisualisering")

if __name__ == "__main__":
    data = get_table()
    create_chart(data)
    # post_to_bluesky() # Avkommentera när du har credentials
