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
        "mag_var": 0.0,
        "lat_lon_valid": 1.0,
        "alt_valid": 1.0,
        "timestamp": 20.0,
        "crs_dev": 0.0,
        "roll_cmd_valid": 0.0,
        "roll_cmd": 0.0,
        "active_freq": 0.0,
        "standby_freq": 0.0,
        "active_freq_ils": 0.0,
        "standby_freq_ils": 0.0,
        "crs_org_dest": 0.0,
        "gsi_deflection": 0.0
    }
    
    def get_p_alt(self) -> float:
        return self.air_data["p_alt"]

    
    def set_p_alt(self, value: float) -> None:
        self.air_data["p_alt"] = value