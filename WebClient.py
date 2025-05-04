import requests
from datetime import timedelta
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

"""
The WebClient class manages the web API connection on the Pi. 
"""
class WebClient:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint


    # Send data using post
    # Format using json 
    def send_event(self, base64_payload: str):
        response = requests.post(
            self.endpoint,
            data=base64_payload,
            headers={"Content-Type": "application/json"},
            verify=False
        )
        response.raise_for_status()


    # Fetch medication data using get
    def fetch_medication(self):
        try:
            # Fetch data using web api
            response = requests.get(
                "https://172.20.10.2:8000/api/getUserMedikamentListe/1",
                verify=False
            )

            if response.status_code != 200:
                print(f"API error: {response.status_code}")
                return []
            raw = response.json()

            # Create flat list to see multiple intake times
            flat_list = []
            for med in raw['list']:
                times = med['timesToTake']
                if isinstance(times, str):
                    times = [times]
                for time in times:
                    flat_list.append({
                        'medikament_navn': med['name'],
                        'tidspunkter_tages': time,
                        'time_interval': f"{int(med['timeInterval'])//60:02}:{int(med['timeInterval'])%60:02}:00",
                    })
            flat_list.sort(key=lambda x: x['tidspunkter_tages'])        # Sort by tidspunkter_tages
            return flat_list

        except Exception as e:
            print(f"Failed to fetch data: {e}")
            return []

