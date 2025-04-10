from datetime import datetime, timedelta

class EnvSim:
    
    def __init__(self):
        self.rooms = {"kitchen", "bedroom", "livingroom", "bathroom", "hallway"}        # initialisere 5 rum i hjemmet
        self.motion_state = {room: False for room in self.rooms}        # sætter aktivitet i alle rum til NULL
        self.meds_taken = False     # simulerer om medicinen er taget
        self.current_time = datetime.now();      # simulerer tiden i minutter 
        

    def advance_time(self, hours: int, minutes: int):
        self.current_time += timedelta(hours=hours, minutes=minutes)        # sætter tiden frem med x antal minutter
        print(f"Tiden er nu: {self.current_time.strftime('%H:%M')}")
    
    
    
    def simulate_motion(self, room: str):
        if room in self.motion_state:       # sikre, at rummet findes
            self.motion_state[room] = True      # simulere bevægelse i valgt rum
            print(f"Bevægelse i {room}")
    
    
    
    def reset_motion(self):
        self.motion_state = {room: False for room in self.rooms}        # sætter aktivitet i alle rum til NULL
       
       
        
    def simulate_meds_taken(self):
        self.meds_taken = True      # simulere at medicinen er taget
        print(f"Medicin er taget")
       
       
        
    def reset(self):        # resetter alle simuleringer
        self.meds_taken = False    
        self.reset_motion()
        
    
