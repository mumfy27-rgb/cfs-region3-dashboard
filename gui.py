# =========================================================
# CFS INCIDENT DASHBOARD
# REGION 3 / STATEWIDE OPERATIONS DASHBOARD
# =========================================================
import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import time
import requests
import pygame
from datetime import datetime
import platform
import json
import math
from bs4 import BeautifulSoup
import feedparser
import cloudscraper
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

if platform.system() == "Windows":
    import winsound


# =========================================================
# CONFIGURATION
# =========================================================
CFS_INCIDENTS_URL = "https://data.eso.sa.gov.au/prod/cfs/criimson/cfs_current_incidents.json"
PAGER_URL = "http://paging1.sacfs.org/cfs.php"
RSS_WARNINGS_URL = "https://www.cfs.sa.gov.au/site/rss/warning_rss.jsp"
RSS_BANS_URL = "https://www.cfs.sa.gov.au/site/rss/bans_rss.jsp"
INCIDENT_LOG_FILE = "incident_log.json"

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

REFRESH_SECONDS = 60
PAGER_REFRESH_SECONDS = 300


# =========================================================
# REGION FILTER
# =========================================================
VALID_REGIONS = [
    "STATEWIDE",
    "REGION 1",
    "REGION 2",
    "REGION 3",
    "REGION 4",
    "REGION 5",
    "REGION 6",
]

def incident_matches_region(incident, filter_mode):
    if filter_mode == "STATEWIDE":
        return True

    region = str(incident.get("Region", "")).upper().strip()

    # REGION 3 -> 3
    wanted_number = filter_mode.replace("REGION", "").strip()

    return (
        region == filter_mode
        or region == wanted_number
        or f"REGION {wanted_number}" in region
        or f"REGION{wanted_number}" in region
    )



# =========================================================
# INCIDENT FETCHING
# =========================================================
def fetch_incidents():
    response = requests.get(CFS_INCIDENTS_URL, timeout=10)
    response.raise_for_status()
    return response.json()


# =========================================================
# UI COLOURS
# =========================================================
def get_incident_colour(incident_type):
    incident_type = str(incident_type).upper()

    if "FIRE" in incident_type:
        return (253, 80, 80)
    if "MVA" in incident_type or "ROADCRASHRESCUE" in incident_type:
        return (255, 220, 80)
    if "RESCUE" in incident_type:
        return (80, 200, 255)
    if "SMOKE" in incident_type:
        return (180, 180, 180)
    if "HAZMAT" in incident_type:
        return (255, 0, 255)
    if "PRESCRIBED" in incident_type:
        return (255, 140, 0)
    if "TREE" in incident_type:
        return (80, 255, 120)

    return (220, 220, 220)


# =========================================================
# DRAWING HELPERS
# =========================================================
def draw_text(screen, text, font, colour, x, y):
    image = font.render(str(text), True, colour)
    screen.blit(image, (x, y))


# =========================================================
# INCIDENT LOGGING
# =========================================================
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


# =========================================================
# INCIDENT STATISTICS
# =========================================================
def calculate_stats(incidents):
    stats = {
        "fire": 0,
        "mva": 0,
        "rescue": 0,
        "hazmat": 0,
        "burn": 0,
        "smoke": 0,
        "tree": 0,
        "other": 0,
    }

    for incident in incidents:
        incident_type = str(incident.get("Type", "")).upper()

        if "FIRE" in incident_type:
            stats["fire"] += 1
        elif "MVA" in incident_type or "VEHICLE ACCIDENT" in incident_type:
            stats["mva"] += 1
        elif "RESCUE" in incident_type:
            stats["rescue"] += 1
        elif "HAZMAT" in incident_type:
            stats["hazmat"] += 1
        elif "SMOKE" in incident_type:
            stats["smoke"] += 1
        elif "PRESCRIBED" in incident_type or "BURN" in incident_type or "BURN OFF" in incident_type:
            stats["burn"] += 1
        elif "TREE" in incident_type:
            stats["tree"] += 1
        else:
            stats["other"] += 1

    return stats


# =========================================================
# PAGER FEED SCRAPER
# =========================================================
scraper = cloudscraper.create_scraper(
    browser={
        "browser": "chrome",
        "platform": "windows",
        "mobile": False,
    }
)

last_pager_message = "No pager message loaded yet."
latest_pager_text = ""
# =============================================================
# FETCH PAGER MESSAGES
# =========================================================== 
def fetch_pager_message():
    try:
        options = webdriver.ChromeOptions()

        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--log-level=3")

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options 
        )

        driver.get(PAGER_URL)

        time.sleep(5)

        body = driver.find_element(By.TAG_NAME, "body").text

        driver.quit()

        return body
    

    except Exception as error:
        print(f"Pager scrape failed: {error}")
        return last_pager_message
    

# ===================================================================================
# FIND MATCHING PAGER MEESAGE
# ====================================================================================
def find_matching_pager_message(pager_text, incident):
    location = str(incident.get("Location_name", "")).upper()
    incident_type = str(incident.get("Type", "")).upper()

    ignored_words = [
        "PAGER TEST",
        "TEST ONLY",
        "TRAINING",
        "REMINDER"
    ]

    messages = pager_text.split("\n")

    best_message = "No matching pager message found."
    best_score = 0

    # BREAK LOCATION INTO WORDS
    location_words = (
        location
        .replace(",", " ")
        .replace("/", " ")
        .split()
    )

    for message in messages:
        msg = message.upper()
        score = 0

        # IGNORE TEST/JUNK
        if any(word in msg for word in ignored_words):
            continue

        # =========================================
        # LOCATION WORD MATCHING
        # =========================================
        for word in location_words:

            # IGNORE SMALL WORDS
            if len(word) <= 3:
                continue

            if word in msg:
                score += 40

        # =========================================
        # INCIDENT TYPE MATCHING
        # =========================================
        if "FIRE" in incident_type and "FIRE" in msg:
            score += 10

        if "HAZMAT" in incident_type and "HAZMAT" in msg:
            score += 15

        if "SMOKE" in incident_type and "SMOKE" in msg:
            score += 15

        if "RESCUE" in incident_type and "RESCUE" in msg:
            score += 15

        if "ASSIST" in incident_type and "ASSIST" in msg:
            score += 15

        # =========================================
        # BEST MATCH
        # =========================================
        if score > best_score:
            best_score = score
            best_message = message

    # REQUIRE A DECENT SCORE
    if best_score >= 40:
        return best_message

    return "No matching pager message found."


# =========================================================
# GOING JOBS TO TOP
# =========================================================
def get_status_priority(incident):
    status = str(incident.get("Status", "")).upper()

    if "GOING" in status:
        return 0
    if "RESPONDING" in status:
        return 1
    if "MONITOR" in status:
        return 2
    if "CONTROLLED" in status:
        return 3

    return 4


# =========================================================
# RSS FEED SCRAPER
# =========================================================
def fetch_rss_feed(url):
    try:
        feed = feedparser.parse(url)
        return feed.entries[:5]
    except Exception:
        return []

 #========================================================================================
    # LOADING SCREEN
    #========================================================================================
def draw_loading_screen(screen, title_font, normal_font, progress, status_text):
    screen.fill((5, 8, 12))

    title = title_font.render("CFS INCIDENT DASHBOARD", True, (240, 240, 240))
    screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 360)))

    loading = normal_font.render("LOADING..........", True, (180, 180, 180))
    screen.blit(loading, loading.get_rect(center=(SCREEN_WIDTH // 2, 460)))

    bar_width = 700
    bar_height = 35
    bar_x = (SCREEN_WIDTH - bar_width) // 2
    bar_y = 520

    pygame.draw.rect(screen, (80, 80, 80), (bar_x, bar_y, bar_width, bar_height), border_radius=12)

    fill_width = int(bar_width * progress)
    pygame.draw.rect(screen, (200, 30, 30), (bar_x, bar_y, fill_width, bar_height), border_radius=12)
        
    pygame.draw.rect(screen, (220, 220, 220), (bar_x, bar_y, bar_width, bar_height), 3, border_radius=12)

    percent = normal_font.render(f"{int(progress * 100)}%", True, (220, 220, 220))
    screen.blit(percent, percent.get_rect(center=(SCREEN_WIDTH // 2, 585)))

    status = normal_font.render(status_text, True, (170, 170, 170))
    screen.blit(status, status.get_rect(center=(SCREEN_WIDTH // 2, 640)))

    pygame.display.flip()

# =========================================================
# MAIN APPLICATION
# =========================================================
def main():
    global last_pager_message, latest_pager_text

    pygame.init()

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("CFS Incident Dashboard")

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
    filter_mode = "STATEWIDE"
    incident_rows = []

    last_refresh_time = 0
    last_pager_refresh_time = 0
    
    error_message = ""
    rss_warnings = []
    rss_bans = []
    TEST_MODE = False

    running = True

    draw_loading_screen(screen, title_font, normal_font, 0.10, "Starting dashboard...")
    pygame.event.pump()

    draw_loading_screen(screen, title_font, normal_font, 0.30, "Fetching incidents...")
    pygame.event.pump()
    all_incidents = fetch_incidents()
    incidents = [
        item for item in all_incidents
        if incident_matches_region(item, filter_mode)
    ]
    incidents.sort(key=get_status_priority)

    draw_loading_screen(screen, title_font, normal_font, 0.55, "Fetching warnings...")
    pygame.event.pump()
    rss_warnings = fetch_rss_feed(RSS_WARNINGS_URL)

    draw_loading_screen(screen, title_font, normal_font, 0.75, "Fetching fire danger ratings...")
    pygame.event.pump()
    rss_bans = fetch_rss_feed(RSS_BANS_URL)

    draw_loading_screen(screen, title_font, normal_font, 0.90, "Fetching pager messages...")
    pygame.event.pump()
    last_pager_message = fetch_pager_message()
    latest_pager_text = last_pager_message

    draw_loading_screen(screen, title_font, normal_font, 1.00, "Dashboard ready...")
    pygame.event.pump()

    pygame.time.delay(100)

    last_updated = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    last_refresh_time = time.time()
    last_pager_refresh_time = time.time()

    # =========================================================
    # MAIN LOOP
    # =========================================================
    while running:
        now = time.time()
        flash_timer += 0.08

        if now - last_refresh_time >= REFRESH_SECONDS or last_refresh_time == 0:
            try:
                if TEST_MODE:
                    all_incidents = [
                        {
                            "IncidentNo": "TEST001",
                            "Type": "Grass Fire",
                            "Status": "GOING",
                            "Location_name": "MURRAY BRIDGE",
                            "Region": "Region 3",
                            "Resources": "20",
                            "Aircraft": "10",
                            "Date": "25/05/2026",
                            "Time": "15:30",
                        },
                        {
                            "IncidentNo": "TEST002",
                            "Type": "HAZMAT",
                            "Status": "GOING",
                            "Location_name": "TAILEM BEND",
                            "Region": "Region 3",
                            "Resources": "4",
                            "Aircraft": "0",
                            "Date": "25/05/2026",
                            "Time": "15:30",
                        },
                        {
                            "IncidentNo": "TEST003",
                            "Type": "Investigate Smoke",
                            "Status": "MONITOR",
                            "Location_name": "MONARTO",
                            "Region": "Region 3",
                            "Resources": "1",
                            "Aircraft": "None",
                            "Date": "25/05/2026",
                            "Time": "17:00",
                        },
                    ]

                    rss_warnings = [
                        {"title": "EMERGENCY WARNING - MURRAY BRIDGE GRASS FIRE"},
                        {"title": "WATCH AND ACT - HAZMAT INCIDENT MONARTO"},
                    ]

                    rss_bans = [
                        {"title": "Murraylands - CATASTROPHIC"},
                        {"title": "Mt Lofty Ranges - CATASTROPHIC"},
                        {"title": "Riverland - EXTREME"},
                    ]

                    latest_pager_text = """
                    MFS: *CFSRES INC0099 27/05/26 16:45 RESPOND VEHICLE ACCIDENT, ALARM LEVEL: 1, : NEAR 19068 STURT HWY MONASH,MAP:RLMM 244 6411,TG 203, ==MVA CLEAN UP REQ :BRI29 MNSH34P
                    MFS: *CFSRES INC0100 25/05/26 15:30 RESPOND GRASSFIRE, ALARM LEVEL: 3, : 584 MAURICE RD ROCKY GULLY LARGE SMOKE PLUME, TG 201, ==GRASS FIRE :MB34P MBQRV  
                    MFS: *CFSRES INC0101 25/05/26 15:30 RESPOND HAZMAT, ALARM LEVEL: 1, : NEAR TAILEM BEND, TG 202, ==LEAKING GAS BULLET :TLMB34P
                    MFS: *CFSRES INC0102 25/05/26 17:00 INVESTIGATE SMOKE, : NEAR MONARTO, TG 204, ==LARGE SMOKE PLUME SIGHTED :MNTO34P
                    """

                else:
                    all_incidents = fetch_incidents()
                    rss_warnings = fetch_rss_feed(RSS_WARNINGS_URL)
                    rss_bans = fetch_rss_feed(RSS_BANS_URL)




                    if (
                        now - last_pager_refresh_time >= PAGER_REFRESH_SECONDS
                        or last_pager_refresh_time == 0
                    ):
                        latest_pager_text = fetch_pager_message()
                        last_pager_refresh_time = now

                incidents = [
                    item for item in all_incidents
                    if incident_matches_region(item, filter_mode)
                ]

                incidents.sort(key=get_status_priority)
                save_incident_log(incidents)

                current_ids = set()

                for item in incidents:
                    current_ids.add(item.get("IncidentNo"))

                new_incident_ids = current_ids - seen_incident_ids

                if new_incident_ids and seen_incident_ids:
                    if platform.system() == "Windows":
                        winsound.Beep(1000, 500)
                    else:
                        print("ALERT")

                seen_incident_ids = current_ids
                last_updated = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                error_message = ""

            except Exception as error:
                error_message = str(error)

            last_refresh_time = now

        # =========================================================
        # EVENT HANDLING
        # =========================================================
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()

                for rect, incident in incident_rows:
                    if rect.collidepoint(mouse_pos):
                        selected_incident = incident

                        # Prescribed burns usually come from the public incident feed only,
                        # so don't try to match them to pager messages.
                        incident_type = str(selected_incident.get("Type", "")).upper()
                    
                        if "PRESCRIBED" in incident_type:
                            last_pager_message = "No Pager Message available for Prescribed Burn"
                        
                        else:
                            
                            last_pager_message = find_matching_pager_message(
                                latest_pager_text,
                                selected_incident
                            )
                        

                        
                       
            if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1:
                        filter_mode = "REGION 1"
                        selected_incident = None
                        last_refresh_time = 0
                        print(f"Filter changed to: {filter_mode}")

                    if event.key == pygame.K_2:
                        filter_mode = "REGION 2"
                        selected_incident = None
                        last_refresh_time = 0
                        print(f"Filter changed to: {filter_mode}")

                    if event.key == pygame.K_3:
                        filter_mode = "REGION 3"
                        selected_incident = None
                        last_refresh_time = 0
                        print(f"Filter changed to: {filter_mode}")

                    if event.key == pygame.K_4:
                        filter_mode = "REGION 4"
                        selected_incident = None
                        last_refresh_time = 0
                        print(f"Filter changed to: {filter_mode}")

                    if event.key == pygame.K_5:
                        filter_mode = "REGION 5"
                        selected_incident = None
                        last_refresh_time = 0
                        print(f"Filter changed to: {filter_mode}")

                    if event.key == pygame.K_6:
                        filter_mode = "REGION 6"
                        selected_incident = None
                        last_refresh_time = 0
                        print(f"Filter changed to: {filter_mode}")

                    if event.key == pygame.K_s:
                        filter_mode = "STATEWIDE"
                        selected_incident = None
                        last_refresh_time = 0
                        print(f"Filter changed to: {filter_mode}")

                    if event.key == pygame.K_t:
                        TEST_MODE = not TEST_MODE
                        selected_incident = None
                        last_refresh_time = 0
                        print(f"Filter changed to: {filter_mode}")

                    if TEST_MODE:
                        print("TEST MODE ENABLED")
                    else:
                        print("LIVE MODE ENABLED")

        # =========================================================
        # DASHBOARD DRAWING
        # =========================================================
        screen.fill((10, 15, 25))

        draw_text(screen, f"PUBLIC CFS {filter_mode} INCIDENT DASHBOARD", title_font, (255, 80, 80), 30, 25)
        draw_text(screen, f"Last updated: {last_updated}", normal_font, (220, 220, 220), 30, 75)
        draw_text(screen, f"Current {filter_mode} incidents: {len(incidents)}", header_font, (255, 255, 255), 30, 115)

        mode_text = "TEST MODE" if TEST_MODE else "LIVE MODE"
        draw_text(screen, f"Mode: {mode_text} | 1-6 = Region Filters | S = Statewide", normal_font, (160, 160, 160), 30, 145)

        pygame.draw.line(screen, (80, 80, 100), (30, 175), (1570, 175), 3)

        incident_rows = []

        if error_message:
            draw_text(screen, "Could not load Public CFS Incident Feed", header_font, (255, 80, 80), 30, 190)
            draw_text(screen, error_message, normal_font, (255, 180, 180), 30, 230)

        elif not incidents:
            draw_text(screen, "No current incidents found.", header_font, (80, 255, 120), 30, 190)

        else:
            y = 205

            # =========================================================
            # INCIDENT LIST
            # =========================================================
            for incident in incidents[:12]:
                incident_type = incident.get("Type")
                colour = get_incident_colour(incident_type)

                row_rect = pygame.Rect(30, y - 8, 1180, 42)
                incident_rows.append((row_rect, incident))

                pygame.draw.rect(screen, (20, 30, 45), row_rect, border_radius=8)
                pygame.draw.rect(screen, colour, (30, y - 8, 8, 42), border_radius=4)

                draw_text(screen, incident.get("IncidentNo"), normal_font, colour, 55, y)

                if incident.get("IncidentNo") in new_incident_ids:
                    flash_value = abs(int(255 * math.sin(flash_timer)))
                    flash_colour = (255, flash_value, 0)

                    pygame.draw.rect(screen, flash_colour, (1110, y - 4, 70, 30), border_radius=6)
                    draw_text(screen, "NEW", normal_font, (0, 0, 0), 1125, y)

                draw_text(screen, incident_type, normal_font, colour, 190, y)
                draw_text(screen, incident.get("Location_name"), normal_font, (230, 230, 230), 460, y)
                draw_text(screen, incident.get("Status"), normal_font, (180, 180, 180), 980, y)

                y += 52

        # =========================================================
        # FIRE DANGER RATINGS PANEL
        # =========================================================
        pygame.draw.rect(screen, (15, 22, 35), (30, 760, 1180, 160), border_radius=10)
        pygame.draw.rect(screen, (80, 80, 100), (30, 760, 1180, 160), 2, border_radius=10)

        draw_text(screen, "FIRE DANGER RATINGS", header_font, (255, 255, 255), 55, 785)

        rating_y = 835

        if not rss_bans:
            draw_text(screen, "No fire danger ratings issued", normal_font, (180, 180, 180), 55, rating_y)
        else:
            for item in rss_bans[:3]:
                title = item.get("title", "Unknown rating")
                draw_text(screen, f"- {title[:85]}", normal_font, (255, 220, 120), 55, rating_y)
                rating_y += 35

        # =========================================================
        # RSS WARNING PANEL
        # =========================================================
        pygame.draw.rect(screen, (15, 22, 35), (30, 930, 980, 160), border_radius=10)
        pygame.draw.rect(screen, (80, 80, 100), (30, 930, 980, 160), 2, border_radius=10)

        draw_text(screen, "CURRENT WARNINGS", header_font, (255, 180, 80), 55, 950)

        warning_y = 990

        if not rss_warnings:
            draw_text(screen, "No current warnings", normal_font, (120, 255, 120), 55, warning_y)
        else:
            for item in rss_warnings[:2]:
                title = item.get("title", "Unknown Warning").upper()

                warning_colour = (220, 220, 220)

                if "EMERGENCY WARNING" in title:
                    warning_colour = (255, 60, 60)
                elif "WATCH AND ACT" in title:
                    warning_colour = (255, 140, 0)
                elif "ADVICE" in title:
                    warning_colour = (255, 220, 80)

                draw_text(screen, f"- {title[:70]}", normal_font, warning_colour, 55, warning_y)
                warning_y += 30

        # =========================================================
        # INCIDENT DETAILS PANEL
        # =========================================================
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

            draw_text(screen, "PAGER MESSAGE:", normal_font, (255, 220, 80), 1250, 570)

            

            clean_pager_message = " ".join(last_pager_message.split())
            words = clean_pager_message.split(" ")


            lines = []
            current_line = ""

            for word in words:
                test_line = current_line + word + " "


                if normal_font.size(test_line)[0] < 430:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word + " "


                
            lines.append(current_line)

            y_pos = 610

            for line in lines[:6]:
                draw_text(screen, line, normal_font, (220, 220, 220), 1250, y_pos)
                y_pos += 35

        else:
            draw_text(screen, "Click an incident on the left.", normal_font, (180, 180, 180), 1250, 240)

        seconds_until_refresh = int(REFRESH_SECONDS - (time.time() - last_refresh_time))
        draw_text(screen, f"Refresh in: {max(seconds_until_refresh, 0)} seconds", normal_font, (160, 160, 160), 1250, 930)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


   



if __name__ == "__main__":
    main()