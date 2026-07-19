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
    ppm_slots = {}

    for team in teams:
        # 1. Beräkna den exakta unika X-positionen baserat på oavrundad PPM
        x_ratio = (team['ppm'] - min_ppm) / ppm_range
        x_pos = int(margin + x_ratio * (width - 2 * margin))
        
        # 2. FIXEN: Vi avrundar till 1 decimal (eller 2 beroende på hur känslig staplingen ska vara)
        # enbart för att se om lagen hamnar i samma vertikala korridor.
        slot_key = round(team['ppm'], 1) 
        count = ppm_slots.get(slot_key, 0)
        
        # Beräkna Y baserat på hur många som redan ligger i denna korridor
        y_pos = height - 180 - (count * (logo_size * 0.75))
        ppm_slots[slot_key] = count + 1
        
        possible_fnames = [f"logos/{team['name']}.png", f"logos/{team['name'].replace(' ', '_')}.png"]
        logo_found = False
        for fname in possible_fnames:
            if os.path.exists(fname):
                try:
                    logo = Image.open(fname).convert("RGBA")
                    logo.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
                    # Klistra in på exakt x_pos men med den staplade y_pos
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
