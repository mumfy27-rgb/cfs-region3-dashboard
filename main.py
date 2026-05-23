import os
import time
import requests
from datetime import datetime
from colorama import Fore, Style, init

init(autoreset=True)

REGION_3_KEYWORDS = [

    # Swanport Group
    "CALLINGTON",
    "ETTRICK",
    "JERVOIS",
    "MANNUM",
    "MONARTO",
    "MURRAY BRIDGE",
    "MYPOLONGA",
    "ROCKLEIGH",
    "TAILEM BEND",

    # Coorong Group
    "COLEBATCH",
    "COOKE PLAINS",
    "COOMANDOOK",
    "COOMBE",
    "COONALPYN",
    "FIELD",
    "JABUK",
    "MENINGIE",
    "NARRUNG",
    "NETHERTON",
    "PEAKE",
    "SALT CREEK",
    "SHERLOCK",
    "MOORLANDS",
    "TINTINARA",

    # Mallee Group
    "BOWHILL",
    "GALGA",
    "GERANIUM",
    "HALIDON",
    "KAROONDA",
    "KULKAMI",
    "MARAMA",
    "LAMEROO",
    "PARILLA",
    "PINNAROO",
    "WYNARKA",

    # Mid Murray Group
    "BLANCHETOWN",
    "CADELL",
    "MORGAN",
    "WAIKERIE",

    # Ridley Group
    "CAMBRAI",
    "KEYNETON",
    "PALMER",
    "SEDAN",
    "SWAN REACH",
    "WALKER FLAT",

    # Chaffey Group
    "BARMERA",
    "BROWNS WELL",
    "GLOSSOP",
    "LYRUP",
    "MONASH",
    "MOOROOK",
    "PARINGA",
    "TAPLAN",
    "WUNKAR",
]


CFS_INCIDENTS_URL = "https://data.eso.sa.gov.au/prod/cfs/criimson/cfs_current_incidents.json"


def fetch_incidents():
    response = requests.get(CFS_INCIDENTS_URL, timeout=10)
    response.raise_for_status()
    return response.json()

def get_incident_colour(incident_type):
      incident_type = str(incident_type).upper()

      if "FIRE" in incident_type:
            return Fore.RED
      
      if "MVA" in incident_type:
            return Fore.YELLOW
      if "RESCUE" in incident_type:
            return Fore.CYAN
      if "TREE DOWN" in incident_type:
            return Fore.GREEN
      if "HAZMAT" in incident_type:
            return Fore.BLUE
      return Fore.WHITE

def is_region_3_incident(incident):
      location = str(incident.get("Location_name", "")).upper()
      region = str(incident.get("Region", "")).upper()
      if "REGION 3" in region:
        return True

        for keyword in REGION_3_KEYWORDS:
            if keyword in location:
                return True

        return False



def show_incidents(incidents):

    region_3_incidents = [
        incident for incident in incidents
        if is_region_3_incident(incident)
    ]

    print("=" * 80)
    print(Fore.RED + "🚒 PUBLIC CFS REGION 3 INCIDENT DASHBOARD 🚒")
    print(f"Updated: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"Region 3 incidents showing: {len(region_3_incidents)}")
    print("=" * 80)

    if not region_3_incidents:
        print()
        print(Fore.GREEN + "No current Region 3 incidents found.")
        return

    for incident in region_3_incidents[:10]:

        incident_type = incident.get("Type")
        colour = get_incident_colour(incident_type)

        print()

        print(colour + "=" * 80)
        print(colour + f"🚨 INCIDENT: {incident.get('IncidentNo')}")
        print(colour + f"TYPE:       {incident_type}")
        print(f"STATUS:     {incident.get('Status')}")
        print(f"REGION:     {incident.get('Region')}")
        print(f"LOCATION:   {incident.get('Location_name')}")
        print(f"RESOURCES:  {incident.get('Resources')}")
        print(f"AIRCRAFT:   {incident.get('Aircraft')}")
        print(f"TIME:       {incident.get('Date')} {incident.get('Time')}")
        print(colour + "=" * 80)


def main():
        while True:
            try:
                    os.system("cls")
                    incidents = fetch_incidents()
                    show_incidents(incidents)
                    print()
                    print("Refreshing every 60 seconds. Press CTRL + C to stop.")

               
                
            except Exception as error:
                print("Could not load public CFS incident feed.")
                print(error)

            time.sleep(60)
        
if __name__ == "__main__":
        main()
