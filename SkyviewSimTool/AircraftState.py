import time
import math

class AircraftState:
    body = {
        "xyz_rate": [0.0, 0.0, 0.0],
        "xyz_accel": [0.0, 0.0, 0.0],
    }
    world = {
        "ypr": [0.0, 0.0, 0.0],
        "ypr_rate": [0.0, 0.0, 0.0]
    }
    air_data = {
        "p_alt": 0.0,
        "vs": 0.0,
        "ias": 0.0,
        "tas": 0.0,
        "aoa": 0.0,
        "oat": 0.0
    }
    gps_data = {
        "lat": 42.0,
        "lon": -122.0,
        "alt": 100.0,
        "gndspd": 0.0,
        "gndtrk": 0.0
    }
    hsi_data = {
        "active_freq_ils": True,
        "standby_freq_ils": True,
        "roll_cmd_valid": True,
        "final_appr_seg": False,
        "lat_lon_valid": True,
        "alt_valid": True,
        "cdi_valid": True,
        "gsi_valid": True,
        "mag_var": 0.0,
        "timestamp": 20.0,
        "crs_dev": -110.0,
        "roll_cmd": 0.0,
        "active_freq": 0.0,
        "standby_freq": 0.0,
        "crs_org_dest": 0.0,
        "gsi_deflection": -110.0
    }

    sim_state = {
        "use msfs" : False,
        "roughSim": False,
        "fake_servos": False
    }

    servo_data = [{
        "motor_position": 0.0,
    },{
        "motor_position": 0.0,
    }]

    prev_time = time.time()


    def positionSim(self, dt):
        print("Simulating position", dt)
        self.gps_data["lat"] += self.gps_data["gndspd"] * dt * math.cos(math.radians(self.gps_data["gndtrk"])) / 111319.9
        self.gps_data["lon"] += self.gps_data["gndspd"] * dt * math.sin(math.radians(self.gps_data["gndtrk"])) / (111319.9 * math.cos(math.radians(self.gps_data["lat"])))
        self.gps_data["alt"] += self.air_data["vs"] * dt * .3048
        self.air_data["p_alt"] = self.gps_data["alt"] * .3048
        self.world["ypr"][0] = (self.gps_data["gndtrk"] + self.hsi_data["mag_var"]) % 360
        self.air_data["ias"] = self.gps_data["gndspd"] * 1.94384
        self.hsi_data["crs_dev"] = self.hsi_data["crs_dev"] - 3 * dt

    def roughSim(self):
        if(self.sim_state["roughSim"]):
            print("Running rough sim")
            self.positionSim(time.time() - self.prev_time)
            self.prev_time = time.time()
        else:
            self.prev_time = time.time()

