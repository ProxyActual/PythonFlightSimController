
try: 
    from .AircraftState import AircraftState
except ImportError:
    from AircraftState import AircraftState

import time
import threading
import socket
import cbor2
import netifaces
from datetime import datetime

frame_check = 1498304334
portNumber = 49301

class AdahrsG4Dat:
    topic = 7
    adahrsAddr = ('ff13::4459:' + hex(topic)[2:], portNumber)
    sequenceNumber = 0
    verticalSpeedFiltered = 0
    running = True

    def __init__(self, sock, aircraft_state):
        self.sock = sock
        self.aircraft_state = aircraft_state
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
        self.verticalSpeedFiltered = (self.verticalSpeedFiltered * VSIfilterCoef) + (self.aircraft_state.air_data["vs"] * (1-VSIfilterCoef))
        

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
                            self.aircraft_state.body["xyz_rate"][0],
                            self.aircraft_state.body["xyz_rate"][1],
                            self.aircraft_state.body["xyz_rate"][2]
                        ],
                        "xyz_acc": [
                            self.aircraft_state.body["xyz_accel"][0],
                            self.aircraft_state.body["xyz_accel"][1],
                            self.aircraft_state.body["xyz_accel"][2]
                        ]
                    },
                    "p_alt": self.aircraft_state.air_data["p_alt"],
                    "vs": self.verticalSpeedFiltered,
                    "ias": self.convert_to_mps(self.aircraft_state.air_data["ias"]),
                    "tas": self.convert_to_mps(self.aircraft_state.air_data["tas"]),
                    "aoa": self.aircraft_state.air_data["aoa"],
                    "oat": self.aircraft_state.air_data["oat"],
                    "world": {
                        "ypr": [ # For whatever reason, MSFS gives these in radians, but specifies them as degrees.
                            self.convert_to_degrees(self.aircraft_state.world["ypr"][0]),
                            -self.convert_to_degrees(self.aircraft_state.world["ypr"][1]),
                            -self.convert_to_degrees(self.aircraft_state.world["ypr"][2])
                        ],
                        "ypr_rate": [
                            self.convert_to_degrees(self.aircraft_state.world["ypr_rate"][0]),
                            self.convert_to_degrees(self.aircraft_state.world["ypr_rate"][1]),
                            self.convert_to_degrees(self.aircraft_state.world["ypr_rate"][2])
                        ]
                    }
                }
            }
        }
        self.sequenceNumber += 1

        return cbor2.dumps(data)


class HsiG4Dat:
    topic = 15
    adahrsAddr = ('ff13::4459:' + hex(topic)[2:], portNumber)
    sequenceNumber = 0
    running = True

    def __init__(self, sock, aircraft_state):
        self.sock = sock
        self.aircraft_state = aircraft_state
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
                        "mag_var": self.aircraft_state.hsi_data["mag_var"],
                        "lat" : self.aircraft_state.gps_data["lat"],
                        "lon" : self.aircraft_state.gps_data["lon"],
                        "alt" : self.aircraft_state.gps_data["alt"],
                        "lat_lon_valid": bool(self.aircraft_state.hsi_data["lat_lon_valid"]),
                        "alt_valid": bool(self.aircraft_state.hsi_data["alt_valid"]),
                        "timestamp": int(self.aircraft_state.hsi_data["timestamp"]),
                        "gndspd": self.aircraft_state.gps_data["gndspd"],
                        "gndtrk": self.aircraft_state.gps_data["gndtrk"]
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
                        "crs_dev": self.aircraft_state.hsi_data["crs_dev"],
                        "roll_cmd_valid": bool(self.aircraft_state.hsi_data["roll_cmd_valid"]),
                        "roll_cmd": self.aircraft_state.hsi_data["roll_cmd"],
                        "active_freq": self.aircraft_state.hsi_data["active_freq"],
                        "standby_freq": self.aircraft_state.hsi_data["standby_freq"],
                        "active_freq_ils": bool(self.aircraft_state.hsi_data["active_freq_ils"]),
                        "standby_freq_ils": bool(self.aircraft_state.hsi_data["standby_freq_ils"]),
                        "crs_org_dest": self.aircraft_state.hsi_data["crs_org_dest"],
                        "gsi_deflection": self.aircraft_state.hsi_data["gsi_deflection"]
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
