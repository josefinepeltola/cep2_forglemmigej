
import requests
from datetime import timedelta
import base64
import json
import sys
from urllib.parse import quote
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

"""
The WebClient class manages the web API connection on the Pi. 
"""
class WebClient:
    # Class initializer 
    def __init__(self):
        self.base_url  = "https://forglemmigej.duckdns.org/api"
        self.__user_id = None
        self.__last_room = None


    # Fetch User id from DB                                             # Harcoded User ID. See DB for running 
    def fetch_userid(self, hardcoded_id=2):
        try:
            url = f"{self.base_url}/getUserId/{hardcoded_id}"
            response = requests.get(url, verify=False)

            if response.status_code != 200:
                print(f"API error: {response.status_code}")
                sys.exit(1)

            data = response.json()
            if data.get("status") == "success":
                self.__user_id = data.get("userId")
                return self.__user_id
            else:
                print("Error from server:", data.get("message"))
                sys.exit(1)
        except Exception as e:
            print(f"Failed to fetch user ID: {e}")
            sys.exit(1)        
        
    
    def fetch_medication(self):
        if self.__user_id is None:
            print("User ID not set. Call fetch_userid() first.")
            return []

        try:
            url = f"{self.base_url}/getUserMedikamentListe/{self.__user_id}"
            response = requests.get(url, verify=False)

            if response.status_code != 200:
                print(f"API error: {response.status_code}")
                return []

            raw = response.json()

            # Decode the Base64-encoded list
            try:
                encoded = raw.get("list")
                decoded_json = base64.b64decode(encoded).decode("utf-8")
                meds = json.loads(decoded_json)
            except Exception as e:
                print(f"Error decoding medication list: {e}")
                return []

            flat_list = []
            for med in meds:
                times = med['timesToTake']
                if isinstance(times, str):
                    times = [times]
                for time in times:
                    flat_list.append({
                        'medikament_navn': med['name'],
                        'tidspunkter_tages': time,
                        'time_interval': f"{int(med['timeInterval'])//60:02}:{int(med['timeInterval'])%60:02}:00",
                    })
            flat_list.sort(key=lambda x: x['tidspunkter_tages'])
            return flat_list

        except Exception as e:
            print(f"Failed to fetch medication data: {e}")
            return []
        

    def send_event(self, url: str, payload, is_base64=False):
        try:
            if is_base64:
                data = payload                                                      # Already base64-encoded string
                headers = {"Content-Type": "application/json"}
            else:
                json_str = json.dumps(payload)
                data = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")
                headers = {"Content-Type": "application/json"}

            response = requests.post(
                url,
                data=data,   # Send raw string, not `json=`
                headers=headers,
                verify=False
            )
            response.raise_for_status()
        except Exception as e:
            print(f"Failed to send event: {e}")



    # Post device status to DB
    def device_status(self, device, event):
        if not device or not event:
            return None

        device_type = device.type_.lower()
        status = None
        power = None
        
        # Get data from sensors using mqtt
        if device_type == "pir":                                    # Check for type
            status = event.get("occupancy", "unknown")              # Get appropiate data for this type
            power = event.get("battery", 0)
            room = device.name_.removeprefix("pir_")                # Find room
            self.__last_room = room

        elif device_type == "vibration":
            status = event.get("vibration", "unknown")
            power = event.get("battery", 0)
            room = device.name_.removeprefix("vibration_")
            self.__last_room = room

        elif device_type == "power plug":
            # status = event.get("state")
            if "state" in event: 
                status = event.get("state")
            else:
                return None
            power = event.get("power", 0)
            room = device.name_.removeprefix("power plug_")
            self.__last_room = room 

        elif device_type == "led":
            status = event.get("state", "unknown")
            power = event.get(0, 0)
            room = device.name_.removeprefix("led_")
            self.__last_room = room

        else:
            print(f"Unknown device type: {device_type}")        # Unknown device
            room = "unknown"                                   
            return None

        # Send Payload to API
        payload = {
            "udstyrData": [
                {
                    "type": device_type,
                    "status": status,
                    "power": power,
                    "lokale": self.__last_room,  
                    "enhed": device_type,
                    "userId": self.__user_id
                }
            ]
        }
        encoded_payload = base64.b64encode(json.dumps(payload).encode()).decode()
        url = f"{self.base_url}/sendUdstyrListeInfo/{self.__user_id}"
        self.send_event(url, encoded_payload, is_base64=True)
        # print("Device status successfully logged")          # Debug, check if data sent 
        
        return payload["udstyrData"][0]
