import time
import requests
import pygame
from datetime import datetime
import winsound
import json
import math

CFS_INCIDENTS_URL = "https://data.eso.sa.gov.au/prod/cfs/criimson/cfs_current_incidents.json"
INCIDENT_LOG_FILE =  "incident_log.json"

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
REFRESH_SECONDS = 60

REGION_3_KEYWORDS = [
    "CALLINGTON", "ETTRICK", "JERVOIS", "MANNUM", "MONARTO",
    "MURRAY BRIDGE", "MYPOLONGA", "ROCKLEIGH", "TAILEM BEND",
    "COLEBATCH", "COOKE PLAINS", "COOMANDOOK", "COOMBE",
    "COONALPYN", "FIELD", "JABUK", "MENINGIE", "NARRUNG",
    "NETHERTON", "PEAKE", "SALT CREEK", "SHERLOCK", "MOORLANDS",
    "TINTINARA", "BOWHILL", "GALGA", "GERANIUM", "HALIDON",
    "KAROONDA", "KULKAMI", "MARAMA", "LAMEROO", "PARILLA",
    "PINNAROO", "WYNARKA", "BLANCHETOWN", "CADELL", "MORGAN",
    "WAIKERIE", "CAMBRAI", "KEYNETON", "PALMER", "SEDAN",
    "SWAN REACH", "WALKER FLAT", "BARMERA", "BROWNS WELL",
    "GLOSSOP", "LYRUP", "MONASH", "MOOROOK", "PARINGA",
    "TAPLAN", "WUNKAR",
]


def fetch_incidents():
    response = requests.get(CFS_INCIDENTS_URL, timeout=10)
    response.raise_for_status()
    return response.json()


def is_region_3_incident(incident):
    location = str(incident.get("Location_name", "")).upper()
    region = str(incident.get("Region", "")).upper()

    if "REGION 3" in region:
        return True

    for keyword in REGION_3_KEYWORDS:
        if keyword in location:
            return True

    return False


def get_incident_colour(incident_type):
    incident_type = str(incident_type).upper()

    if "FIRE" in incident_type:
        return (253, 80, 80)

    if "MVA" in incident_type or "ROADCRASHRESCUE" in incident_type:
        return (255, 220, 80)

    if "RESCUE" in incident_type:
        return (80, 200, 255)

    if "TREE" in incident_type:
        return (80, 255, 120)

    return (220, 220, 220)


def draw_text(screen, text, font, colour, x, y):
    image = font.render(str(text), True, colour)
    screen.blit(image, (x, y))

def save_incident_log(incidents):
    log_entry = {
        "saved_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "incident_count": len(incidents),
        "incidents": incidents,
    }
    try:
        with open(INCIDENT_LOG_FILE, "a") as file:
            file.write(json.dumps(log_entry))
            file.write("\n")


    except Exception as error:
        print(f"Could not save incident log: {error}")

def calculate_stats(incidents):
    stats = {
        "fire": 0,
        "mva": 0,
        "rescue": 0,
        "tree": 0, 
        "other": 0,
    }

    for incident in incidents:
        incident_type = str(incident.get("Type", "")).upper()

        if "FIRE" in incident_type:
            stats["fire"] += 1

        elif "MVA" in incident_type:
            stats["mva"] += 1

        elif "RESCUE" in incident_type:
            stats["rescue"] += 1

        elif "TREE" in incident_type:
            stats["tree"] += 1

        else:
            stats["other"] += 1

    return stats

def lation_to_screen(lat, lon):
    #  rough region 3 bonding box
    min_lat = -36.5
    max_lat = -33.8
    min_lon = 138.5
    max_lon = 141.2

    map_x = 30
    map_y = 930
    map_width = 1180
    map_height = 120

    x = map_x + ((lon - min_lon) / (max_lon - min_lon))* map_width
    y = map_y + ((max_lat - lat) / (max_lat - min_lat))* map_height

    return int(x), int(y)



def main():
    pygame.init()

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("CFS Region 3 Incident Dashboard")

    title_font = pygame.font.SysFont("consolas", 42, bold=True)
    header_font = pygame.font.SysFont("consolas", 30, bold=True)
    normal_font = pygame.font.SysFont("consolas", 24)

    seen_incident_ids = set()
    new_incident_ids = set()

    clock = pygame.time.Clock()
    flash_timer = 0

    incidents = []
    last_updated = "Never"
    selected_incident = None
    incident_rows = []
    last_refresh_time = 0
    error_message = ""

    running = True

    while running:
        now = time.time()
        flash_timer += 0.08

        if now - last_refresh_time >= REFRESH_SECONDS or last_refresh_time == 0:
            try:
                all_incidents = fetch_incidents()
                incidents = [
                    incident for incident in all_incidents
                    if is_region_3_incident(incident)
                ]
                save_incident_log(incidents)

                current_ids = {
                    incident.get("IncidentNo")
                    for incident in incidents
                }

                new_incident_ids = current_ids - seen_incident_ids

                if new_incident_ids and seen_incident_ids:
                    winsound.Beep(1000, 500)

                seen_incident_ids = current_ids
                last_updated = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                error_message = ""

            except Exception as error:
                error_message = str(error)

            last_refresh_time = now

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()

                for rect, incident in incident_rows:
                    if rect.collidepoint(mouse_pos):
                        selected_incident = incident

        screen.fill((10, 15, 25))

        draw_text(screen, "PUBLIC CFS REGION 3 INCIDENT DASHBOARD", title_font, (255, 80, 80), 30, 25)
        draw_text(screen, f"Last updated: {last_updated}", normal_font, (220, 220, 220), 30, 75)
        draw_text(screen, f"Current Region 3 incidents: {len(incidents)}", header_font, (255, 255, 255), 30, 115)

        pygame.draw.line(screen, (80, 80, 100), (30, 150), (1570, 150), 2)

        incident_rows = []

        if error_message:
            draw_text(screen, "Could not load Public CFS Incident Feed", header_font, (255, 80, 80), 30, 180)
            draw_text(screen, error_message, normal_font, (255, 180, 180), 30, 215)

        elif not incidents:
            draw_text(screen, "No Current Region 3 incidents found.", header_font, (80, 255, 120), 30, 190)

        else:
            y = 180

            for incident in incidents[:12]:
                incident_type = incident.get("Type")
                colour = get_incident_colour(incident_type)

                row_rect = pygame.Rect(30, y - 8, 700, 42)
                incident_rows.append((row_rect, incident))

                pygame.draw.rect(screen, (20, 30, 45), row_rect, border_radius=8)
                pygame.draw.rect(screen, colour, (30, y - 8, 8, 42), border_radius=4)

                draw_text(screen, incident.get("IncidentNo"), normal_font, colour, 55, y)

                if incident.get("IncidentNo") in new_incident_ids:
                    

                    flash_value = abs(int(255 * math.sin(flash_timer)))


                    flash_colour = (255, flash_value,0)

                    pygame.draw.rect(
                        screen,
                        flash_colour,
                        (1110, y - 4, 70, 30),
                        border_radius= 6
                    )

                    draw_text(screen, "NEW", normal_font, (0, 0, 0), 1125, y)

                draw_text(screen, incident_type, normal_font, colour, 190, y)
                draw_text(screen, incident.get("Location_name"), normal_font, (230, 230, 230), 460, y)
                draw_text(screen, incident.get("Status"), normal_font, (180, 180, 180), 980, y)

                y += 52

        pygame.draw.rect(screen, (15, 22, 35), (1250, 170, 620, 800), border_radius=10)
        pygame.draw.rect(screen, (80, 80, 100), (1250, 170, 620 ,800), 2, border_radius=10)

        draw_text(screen, "INCIDENT DETAILS", header_font, (255, 255, 255), 1280, 190)


        stats = calculate_stats(incidents)

        pygame.draw.rect(screen, (15, 22, 35), (30, 760, 1180, 160), border_radius=10)
        pygame.draw.rect(screen, (80, 80, 100), (30, 760, 1180, 160), 2, border_radius=10)

        draw_text(screen, "INCIDENT STATS", header_font, (255, 255, 255), 55, 785)

        draw_text(screen, f"FIRES: {stats['fire']}", normal_font, (253, 80, 80), 55, 835)
        draw_text(screen, f"MVA: {stats['mva']}", normal_font, (255, 220, 80), 250, 835)
        draw_text(screen, f"RESCUE: {stats['rescue']}", normal_font, (80, 200, 255), 420, 835)
        draw_text(screen, f"TREE: {stats['tree']}", normal_font, (80, 255, 120), 650, 835)
        draw_text(screen, f"OTHER: {stats['other']}", normal_font, (220, 220, 220), 850, 835)



        if selected_incident is not None:
            detail_type = selected_incident.get("Type")
            detail_colour = get_incident_colour(detail_type)

            draw_text(screen, f"Incident: {selected_incident.get('IncidentNo')}", normal_font, detail_colour, 1250, 240)
            draw_text(screen, f"Type: {detail_type}", normal_font, detail_colour, 1250, 275)
            draw_text(screen, f"Status: {selected_incident.get('Status')}", normal_font, (220, 220, 220), 1250, 310)
            draw_text(screen, f"Region: {selected_incident.get('Region')}", normal_font, (220, 220, 220), 1250, 345)
            draw_text(screen, f"Location: {selected_incident.get('Location_name')}", normal_font, (220, 220, 220), 1250, 380)
            draw_text(screen, f"Resources: {selected_incident.get('Resources')}", normal_font, (220, 220, 220), 1250, 415)
            draw_text(screen, f"Aircraft: {selected_incident.get('Aircraft')}", normal_font, (220, 220, 220), 1250, 450)
            draw_text(screen, f"Date: {selected_incident.get('Date')}", normal_font, (220, 220, 220), 1250, 485)
            draw_text(screen, f"Time: {selected_incident.get('Time')}", normal_font, (220, 220, 220), 1250, 520)

        else:
            draw_text(screen, "Click an incident on the left.", normal_font, (180, 180, 180), 1250, 240)

        seconds_until_refresh = int(REFRESH_SECONDS - (time.time() - last_refresh_time))

        pygame.draw.rect(screen, (15, 22, 35), (30, 930, 1180, 120), border_radius=10)
        pygame.draw.rect(screen, (80, 80, 100), (30, 930, 1180, 120), 2, border_radius=10)

        draw_text(screen, "REGION 3 MAP VIEW", header_font, (255, 255, 255), 55, 950)

        mapped_incidents = 0

        for incident in incidents:
            try:
                lat = float(incident.get("Latitude"))
                lon = float(incident.get("Longitude"))

                x, y = lation_to_screen(lat, lon)
                mapped_incidents += 1

                incident_type = incident.get("Typw")
                colour = get_incident_colour(incident_type)

                radius = 8

                if incident.get("IncidentNO") in new_incident_ids:
                    radius = 8 + int(abs(6 * math.sin(flash_timer)))
                
                pygame.draw.circle(screen, colour, (x, y), radius)
                pygame.draw.circle(screen, (255, 255, 255), (x, y). radius, 2)

            except:
                pass

            if mapped_incidents == 0:
                draw_text(
                    screen,
                    "No Mappable incidents",
                    normal_font,
                    (180, 180, 180),
                    55,
                    995
                )

        draw_text(screen, f"Refresh in: {max(seconds_until_refresh, 0)} seconds", normal_font, (160, 160, 160), 1250, 1010)


        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main() 