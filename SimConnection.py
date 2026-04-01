
from SimConnect import *
import time
import random
import threading
import socket
import cbor2
import tkinter as tk
import netifaces
from datetime import datetime
from math import cos, sin, radians, degrees

frame_check = 1498304334
portNumber = 49301

# Map of default values for each data type
default_values = {
    "VERTICAL_SPEED": 400.0,
    "ROTATION_VELOCITY_BODY_X": 0.0,
    "ROTATION_VELOCITY_BODY_Y": 0.0,
    "ROTATION_VELOCITY_BODY_Z": 0.0,
    "TURN_COORDINATOR_BALL": 0.0,
    "G_FORCE": 1.0,
    "PRESSURE_ALTITUDE": 1500.0,
    "AIRSPEED_INDICATED": 300.0,
    "AIRSPEED_TRUE": 300.0,
    "INCIDENCE_ALPHA": 0.0,
    "STANDARD_ATM_TEMPERATURE": 15.0,
    "PLANE_HEADING_DEGREES_MAGNETIC": 40.0,
    "PLANE_PITCH_DEGREES": 0.0,
    "PLANE_BANK_DEGREES": 0.0,
    "PLANE_LATITUDE": 47.0,
    "PLANE_LONGITUDE": -122.0,
    "GPS MAGVAR": 0.0,

    "NAV_ACTIVE_FREQUENCY:1": 109.6,
    "NAV_STANDBY_FREQUENCY:1": 110.3,
    "NAV_CDI:1": 110,
    "NAV_OBS:1": 62.0,
    "HSI_HAS_LOCALIZER": 1.0,
    "HSI_GSI_NEEDLE": 0.0,
    "GPS_GROUND_MAGNETIC_TRACK": 90.0
}

class DataThread:
    value = 0
    is_running = True
    simConnected = False
    last_update = time.time()
    ValLock = threading.Lock()
    timeLock = threading.Lock()
    fps = 0

    def __init__(self, dataTarget):
        self.dataTarget = dataTarget
        try:
            self.sm = SimConnect()
            self.aq = AircraftRequests(self.sm, _time=16)
            self.simConnected = True
        except Exception as e:
            self.simConnected = False
        
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        while True:
            # Check if the thread is safe to run
            value = 0
            if(self.simConnected):
                value = self.aq.get(self.dataTarget)
            else:
                if self.dataTarget in default_values:
                    value = default_values[self.dataTarget]
                time.sleep(0.001)
            
            self.ValLock.acquire()
            self.value = value
            self.ValLock.release()

            delta = time.time() - self.last_update
            # Avoid divide by zero if the update is too fast
            while delta == 0:
                time.sleep(0.001)
                delta = time.time() - self.last_update
            self.timeLock.acquire()
            self.fps = ((1 / delta) * .01) + (self.fps * 0.99)
            self.timeLock.release()
            self.last_update = time.time()
    
    def get_value(self):
        self.ValLock.acquire()
        value = self.value
        self.ValLock.release()
        return value
    
    def get_fps(self):
        self.timeLock.acquire()
        fps = self.fps
        self.timeLock.release()
        return fps
    
    def get_is_connected(self):
        return self.simConnected

class DataManager:
    values = {}

    def __init__(self):
        pass

    def addValue(self, name):
        if name not in self.values:
            self.values[name] = DataThread(name)

    def get_value(self, name):
        self.addValue(name)
        return self.values[name].get_value()

    def get_value_safe(self, name):
        value = self.get_value(name)
        if value is None:
            return 0.0
        return value

    def get_fps(self, name):
        self.addValue(name)
        return self.values[name].get_fps()

    def get_is_connected(self, name):
        self.addValue(name)
        return self.values[name].get_is_connected()
    
    def get_all_values(self):
        all_values = {name: thread.get_value() for name, thread in self.values.items()}
        return all_values

class DisplayManager:
    lineCount = 0
    maxLines = 30
    maxWidth = 100
    debug = False


    def __init__(self):
        pass

    def print_line(self, text):
        if(not self.debug):
            print("\033[K" + text)
        self.lineCount += 1
    
    def resetPointer(self):
        for _ in range(self.lineCount):
            if(not self.debug):
                print("\033[F", end="")
        self.lineCount = 0

class AdahrsSim:
    topic = 7
    adahrsAddr = ('ff13::4459:' + hex(topic)[2:], portNumber)
    sequenceNumber = 0
    verticalSpeedFiltered = 0
    running = True

    def __init__(self, data_manager, sock):
        self.data_manager = data_manager
        self.sock = sock
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        last_time = time.time()
        while self.running:
            if(time.time() - last_time > 1.0/65.0):
                self.sock.sendto(self.get_cbor_packet(), self.adahrsAddr)
                last_time = time.time()
            else:
                time.sleep(0.001)

    def convert_to_degrees(self, radians):
        return radians * (180.0 / 3.141592653589793)

    def convert_to_mps(self, knots):
        return knots * 0.514444

    def get_cbor_packet(self):
        VSIfilterCoef = 0.95
        self.verticalSpeedFiltered = (self.verticalSpeedFiltered * VSIfilterCoef) + (self.data_manager.get_value_safe("VERTICAL_SPEED") * (1-VSIfilterCoef))
        

        data = {
            "d": frame_check,
            "seq": self.sequenceNumber,
            "topic": self.topic,
            "txid": 0,
            "payload": {
                "AhrsG4Dat_V1": {
                    "version" : 1,
                    "valid": True,
                    "tick": self.sequenceNumber,
                    "body": {
                        "xyz_rate": [
                            self.data_manager.get_value_safe("ROTATION_VELOCITY_BODY_X"),
                            self.data_manager.get_value_safe("ROTATION_VELOCITY_BODY_Y"),
                            float(self.data_manager.get_value_safe("ROTATION_VELOCITY_BODY_Z")  * 57.2958 / 3.28)
                        ],
                        "xyz_acc": [
                            0.0,
                            -self.data_manager.get_value_safe("TURN_COORDINATOR_BALL") * -.3,
                            -self.data_manager.get_value_safe("G_FORCE")
                        ]
                    },
                    "p_alt": self.data_manager.get_value_safe("PRESSURE_ALTITUDE"),
                    "vs": self.verticalSpeedFiltered,
                    "ias": self.convert_to_mps(self.data_manager.get_value_safe("AIRSPEED_INDICATED")),
                    "tas": self.convert_to_mps(self.data_manager.get_value_safe("AIRSPEED_TRUE")),
                    "aoa": self.data_manager.get_value_safe("INCIDENCE_ALPHA"),
                    "oat": self.data_manager.get_value_safe("STANDARD_ATM_TEMPERATURE") - 460.0,
                    "world": {
                        "ypr": [ # For whatever reason, MSFS gives these in radians, but specifies them as degrees.
                            self.convert_to_degrees(self.data_manager.get_value_safe("PLANE_HEADING_DEGREES_MAGNETIC")),
                            -self.convert_to_degrees(self.data_manager.get_value_safe("PLANE_PITCH_DEGREES")),
                            -self.convert_to_degrees(self.data_manager.get_value_safe("PLANE_BANK_DEGREES"))
                        ],
                        "ypr_rate": [
                            0.0,
                            0.0,
                            0.0
                        ]
                    }
                }
            }
        }
        self.sequenceNumber += 1

        return cbor2.dumps(data)


class HsiSim:
    topic = 15
    adahrsAddr = ('ff13::4459:' + hex(topic)[2:], portNumber)
    sequenceNumber = 0
    running = True

    def __init__(self, data_manager, sock):
        self.data_manager = data_manager
        self.sock = sock
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
    
    def run(self):
        last_time = time.time()
        while self.running:
            if(time.time() - last_time > 1.0/64.0):
                packet = self.get_cbor_packet()
                if(self.sequenceNumber > 16):
                    self.sock.sendto(packet, self.adahrsAddr)
                last_time = time.time()
            else:
                time.sleep(0.001)
    
    def get_cbor_packet(self):
        data = {
            "d": frame_check,
            "seq": self.sequenceNumber,
            "topic": self.topic,
            "txid": 0,
            "payload": {
                "HsiG4Dat_V1": {
                    "version" : 1,
                    "valid": True,
                    "tick": self.sequenceNumber,
                    "pos": {
                        "mag_var": float(self.data_manager.get_value_safe("GPS MAGVAR")),
                        "lat" : float(self.data_manager.get_value_safe("PLANE_LATITUDE")),
                        "lon" : float(self.data_manager.get_value_safe("PLANE_LONGITUDE")),
                        "alt" : float(self.data_manager.get_value_safe("PRESSURE_ALTITUDE")),
                        "lat_lon_valid": True,
                        "alt_valid": True,
                        "timestamp": 20,
                        "gndspd": float(self.data_manager.get_value_safe("GROUND_VELOCITY")),
                        "gndtrk": float(self.data_manager.get_value_safe("GPS_GROUND_MAGNETIC_TRACK") * (3.141592653589793 / 180.0))
                    },
                    "time": {
                        "y": datetime.utcnow().year,
                        "m": datetime.utcnow().month,
                        "d": datetime.utcnow().day,
                        "h": datetime.utcnow().hour,
                        "min": datetime.utcnow().minute,
                        "s": datetime.utcnow().second
                    },
                    "nav": {
                        "crs_dev": float(self.data_manager.get_value_safe("NAV_CDI:1")),
                        "roll_cmd_valid": False,
                        "roll_cmd": float(0.0),
                        "active_freq": float(self.data_manager.get_value_safe("NAV_ACTIVE_FREQUENCY:1") * 1000),
                        "standby_freq": float(self.data_manager.get_value_safe("NAV_STANDBY_FREQUENCY:1") * 1000),
                        "active_freq_ils": True if self.data_manager.get_value_safe("HSI_HAS_LOCALIZER") == 1.0 else False,
                        "standby_freq_ils": False,
                        "crs_org_dest": float(self.data_manager.get_value_safe("NAV_OBS:1")),
                        "gsi_deflection": float(self.data_manager.get_value_safe("HSI_GSI_NEEDLE"))
                    }
                }
            }
        }
        self.sequenceNumber += 1

        return cbor2.dumps(data)

class gen4Network:
    sock = None

    def __init__(self):
         # Automatically find the last two hex values from network interfaces
        last_two_hex = None
        for interface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET6 in addrs:
                for addr_info in addrs[netifaces.AF_INET6]:
                    addr = addr_info['addr'].split('%')[0]  # Remove scope ID if present
                    # Look for fd44:594e:4f4e:1:: prefix
                    if addr.startswith('fd44:594e:4f4e:1::') and addr != 'fd44:594e:4f4e:1::':
                        # Extract the last part after the prefix
                        last_part = addr.replace('fd44:594e:4f4e:1::', '')
                        if last_part:
                            last_two_hex = last_part
                            print(f"Found Gen4 interface: {interface} - {addr}")
                            break
            if last_two_hex:
                break

        if not last_two_hex:
            last_two_hex = input("Could not auto-detect. Enter the last two hex values for Gen4 address (e.g. '43' for fd44:594e:4f4e:1::43): ").strip()
        gen4NetworkInterfaceAddress = f"fd44:594e:4f4e:1::{last_two_hex}"

        self.sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self.sock.bind((gen4NetworkInterfaceAddress, portNumber))


def calculate_position_change(magnetic_heading, true_airspeed, delta_time, lat, lon, magnetic_declination=0.0):
    """
    Calculate the change in latitude and longitude based on magnetic heading, true airspeed, and time.
    
    Args:
        magnetic_heading: Aircraft heading in degrees (0-360, magnetic north)
        true_airspeed: True airspeed in knots
        delta_time: Time delta in seconds
        lat: Current latitude in decimal degrees
        lon: Current longitude in decimal degrees
        magnetic_declination: Magnetic declination in degrees (positive = east, negative = west)
    
    Returns:
        tuple: (delta_lat, delta_lon) change in decimal degrees
    """
    # Constants
    EARTH_RADIUS_NM = 3440.06  # Earth's radius in nautical miles
    
    # Convert magnetic heading to true heading
    true_heading = (magnetic_heading + magnetic_declination) % 360.0
    
    # Distance traveled in nautical miles
    distance_nm = true_airspeed * (delta_time / 3600.0)
    
    # Convert heading to radians
    heading_rad = radians(true_heading)
    lat_rad = radians(lat)
    
    # Calculate changes using spherical Earth approximation (haversine-based)
    # For small distances, this is accurate enough
    delta_lat = distance_nm * cos(heading_rad) / 60.0  # 1 nautical mile = 1 minute of latitude
    
    # Longitude changes need to account for latitude convergence
    # At the equator, 1 minute longitude = 1 nautical mile
    # At higher latitudes, longitude distance decreases
    new_lat_rad = radians(lat + delta_lat)
    delta_lon = distance_nm * sin(heading_rad) / (60.0 * cos(new_lat_rad))
    
    return (delta_lat, delta_lon)


def aircraftSim(delta_time):
    tas = default_values["AIRSPEED_TRUE"]
    magnetic_heading = default_values["PLANE_HEADING_DEGREES_MAGNETIC"]
    magnetic_declination = default_values["GPS MAGVAR"]
    lat = default_values["PLANE_LATITUDE"]
    lon = default_values["PLANE_LONGITUDE"]

    if(default_values["GPS_GROUND_MAGNETIC_TRACK"] >= 360.0):
        default_values["GPS_GROUND_MAGNETIC_TRACK"] = 0.0

    default_values["VERTICAL_SPEED"] = 400.0 * sin(time.time()) # Simulate a vertical speed oscillation

    default_values["PRESSURE_ALTITUDE"] += default_values["VERTICAL_SPEED"] * delta_time / 60.0 # Convert feet per minute to feet per second
    default_values["HSI_GSI_NEEDLE"] = 1000 * sin(time.time()) # Simulate a GSI needle oscillation

    default_values["PLANE_HEADING_DEGREES_MAGNETIC"] = (default_values["GPS_GROUND_MAGNETIC_TRACK"]) % 360

    # Calculate position change accounting for Earth's shape and magnetic declination
    delta_lat, delta_lon = calculate_position_change(
        magnetic_heading, 
        tas, 
        delta_time, 
        lat, 
        lon, 
        magnetic_declination
    )
    
    default_values["PLANE_LATITUDE"] += delta_lat
    default_values["PLANE_LONGITUDE"] += delta_lon

    default_values["PLANE_PITCH_DEGREES"] = radians(-5.0 * default_values["VERTICAL_SPEED"] / 400.0) # Simulate a pitch oscillation
    default_values["PLANE_BANK_DEGREES"] = radians(10.0 * sin(time.time()/10)) # Simulate a bank oscillation
    default_values["GPS_GROUND_MAGNETIC_TRACK"] -= default_values["PLANE_BANK_DEGREES"] # Simulate a constant turn to the right
    default_values["NAV_CDI:1"] = 1 * sin(time.time()) # Simulate a CDI oscillation

def main():
    print("Starting Data Manager...")
    DSM = DisplayManager()
    DM = DataManager()
    DM.get_value("NAV_CDI:2")
    start_time = time.time()
    # Get user input for the last two hex values of the Gen4 network interface address
    # Automatically find the last two hex values from network interfaces
    last_two_hex = None
    for interface in netifaces.interfaces():
        addrs = netifaces.ifaddresses(interface)
        if netifaces.AF_INET6 in addrs:
            for addr_info in addrs[netifaces.AF_INET6]:
                addr = addr_info['addr'].split('%')[0]  # Remove scope ID if present
                # Look for fd44:594e:4f4e:1:: prefix
                if addr.startswith('fd44:594e:4f4e:1::') and addr != 'fd44:594e:4f4e:1::':
                    # Extract the last part after the prefix
                    last_part = addr.replace('fd44:594e:4f4e:1::', '')
                    if last_part:
                        last_two_hex = last_part
                        print(f"Found Gen4 interface: {interface} - {addr}")
                        break
        if last_two_hex:
            break

    if not last_two_hex:
        last_two_hex = input("Could not auto-detect. Enter the last two hex values for Gen4 address (e.g. '43' for fd44:594e:4f4e:1::43): ").strip()
    gen4NetworkInterfaceAddress = f"fd44:594e:4f4e:1::{last_two_hex}"

    sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    sock.bind((gen4NetworkInterfaceAddress, portNumber))

    adahrs = AdahrsSim(DM, sock)
    hsi = HsiSim(DM, sock)
    last_time = time.time()

    while(True):
        values = DM.get_all_values()
        if(not DM.get_is_connected("VERTICAL_SPEED")):
            aircraftSim(time.time() - last_time)
        last_time = time.time()
        DSM.resetPointer()
        DSM.print_line(f"Up Time: {time.time() - start_time:.2f}s")
        DSM.print_line(f"{'DataName':<30} | {'Value':>10} | {'FPS':>10} | {'Connected':<10} | {'Status'}")
        DSM.print_line("-" * 100)
        for name, value in values.items():
            bad_val = False
            if(value is None):
                value = 0.0
                bad_val = True
            if(name == "PLANE_LONGITUDE"):
                connected = "Yes" if DM.get_is_connected(name) else "No"
                fps = DM.get_fps(name)
                fps_str = f"{fps:.1f}" if fps < 1000 else f"{fps:.0f}"
                DSM.print_line(f"{name:<30} | {value:>10.2f} | {fps_str:>10} | {connected:<10} | {'BAD' if bad_val else ''}")
        
        time.sleep(0.016)

if __name__ == "__main__":
    main()
