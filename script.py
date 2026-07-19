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
    
    # Sortera: lägst PPM först. Vid lika PPM hamnar högre rank överst.
    teams.sort(key=lambda x: (x['ppm'], -x['rank']))
    
    # Vi sparar koordinaterna för de logotyper vi redan har ritat ut
    # Format: (x_center, y_center)
    placed_logos = []

    for team in teams:
        # 1. Beräkna den exakta unika X-positionen baserat på oavrundad PPM
        x_ratio = (team['ppm'] - min_ppm) / ppm_range
        x_pos = int(margin + x_ratio * (width - 2 * margin))
        
        # 2. Hitta rätt Y-nivå genom att kontrollera om vi krockar horisontellt med en befintlig logotyp
        current_level = 0
        while True:
            # Beräkna potentiell Y-position för denna nivå
            pot_y = height - 180 - (current_level * (logo_size * 0.75))
            
            # Kolla om vi krockar med NÅGON logotyp på samma Y-nivå inom 60 pixlars avstånd i X-led
            collision = False
            for px, py in placed_logos:
                if abs(py - pot_y) < 5: # Samma Y-nivå (med lite felmarginal)
                    if abs(px - x_pos) < 60: # För nära i X-led (logotyperna skulle överlappa fult)
                        collision = True
                        break
            
            if collision:
                # Om det krockar, testa nästa nivå uppåt
                current_level += 1
            else:
                # Ingen krock funnen på denna nivå, vi tar den!
                y_pos = pot_y
                break
                
        # Spara den valda positionen
        placed_logos.append((x_pos, y_pos))
        
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
                except: continue
        if not logo_found:
            draw.text((x_pos, int(y_pos)), team['name'], fill="black")

    draw.line((margin, height - 120, width - margin, height - 120), fill="black", width=3)
    draw.text((margin, height - 100), f"{min_ppm:.2f} PPM", fill="black", font=font_sub)
    draw.text((width - margin - 80, height - 100), f"{max_ppm:.2f} PPM", fill="black", font=font_sub)
    
    img.convert("RGB").save("allsvenskan_ppm.jpg", "JPEG", quality=95)
    return True
