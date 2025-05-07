import requests
from datetime import timedelta
import base64
import json
from urllib.parse import quote
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

"""
The WebClient class manages the web API connection on the Pi. 
"""
class WebClient:
    # Class initializer 
    def __init__(self):
        self.base_url = "https://172.20.10.2:8000/api"
        self.__user_id = None
        self.__last_room = None


    """
    CANNOT DYNAMICALLY FIND USER ID - IS HARDCODED
    """
    # Fetch User id from DB
    def fetch_userid(self, hardcoded_id=1):
        try:
            url = f"{self.base_url}/getUserId/{hardcoded_id}"
            response = requests.get(url, verify=False)

            if response.status_code != 200:
                print(f"API error: {response.status_code}")
                return None

            data = response.json()
            if data.get("status") == "success":
                self.__user_id = data.get("userId")
                return self.__user_id
            else:
                print("Error from server:", data.get("message"))
                return None
        except Exception as e:
            print(f"Failed to fetch user ID: {e}")
            return None        


    # Fetch medication from DB for given user id
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

            # Initialize as list, to handle multiple intake times
            raw = response.json()                                                           
            flat_list = []
            for med in raw.get('list', []):
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
        

    # Post event to DB
    def send_event(self, url: str, payload: dict):
        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
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
        url = f"{self.base_url}/sendUdstyrListeInfo/{self.__user_id}"
        self.send_event(url, payload)
        # print("Device status successfully logged")          # Debug, check if data sent 
        
        return payload["udstyrData"][0]
    
