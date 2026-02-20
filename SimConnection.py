
from SimConnect import *
import time
import random
import threading
import socket
import cbor2
import tkinter as tk
import netifaces

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
    "AIRSPEED_INDICATED": 0.0,
    "AIRSPEED_TRUE": 0.0,
    "INCIDENCE_ALPHA": 0.0,
    "STANDARD_ATM_TEMPERATURE": 15.0,
    "PLANE_HEADING_DEGREES_MAGNETIC": 0.0,
    "PLANE_PITCH_DEGREES": 0.0,
    "PLANE_BANK_DEGREES": 0.0,
    "PLANE_LATITUDE": 47.0,
    "PLANE_LONGITUDE": -122.0
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
                            self.data_manager.get_value_safe("ROTATION_VELOCITY_BODY_Z")
                        ],
                        "xyz_acc": [
                            0.0,
                            -self.data_manager.get_value_safe("TURN_COORDINATOR_BALL"),
                            -self.data_manager.get_value_safe("G_FORCE")
                        ]
                    },
                    "p_alt": self.data_manager.get_value_safe("PRESSURE_ALTITUDE"),
                    "vs": self.verticalSpeedFiltered,
                    "ias": self.convert_to_mps(self.data_manager.get_value_safe("AIRSPEED_INDICATED")),
                    "tas": self.convert_to_mps(self.data_manager.get_value_safe("AIRSPEED_TRUE")),
                    "aoa": self.data_manager.get_value_safe("INCIDENCE_ALPHA"),
                    "oat": self.data_manager.get_value_safe("STANDARD_ATM_TEMPERATURE"),
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
            if(time.time() - last_time > 1.0/17.0):
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
                        "mag_var": 0.0,
                        "lat" : self.data_manager.get_value_safe("PLANE_LATITUDE"),
                        "lon" : self.data_manager.get_value_safe("PLANE_LONGITUDE"),
                        "alt" : self.data_manager.get_value_safe("PRESSURE_ALTITUDE"),
                        "lat_lon_valid": True,
                        "alt_valid": True,
                        "timestamp": 20,
                        "gndspd": self.data_manager.get_value_safe("GROUND_VELOCITY"),
                        "gndtrk": 90.0
                    },
                    "time": {
                        "y": time.localtime().tm_year,
                        "m": time.localtime().tm_mon,
                        "d": time.localtime().tm_mday,
                        "h": time.localtime().tm_hour,
                        "min": time.localtime().tm_min,
                        "s": time.localtime().tm_sec
                    },
                    "nav": {
                        "crs_dev": 20.0,
                        "active_freq": 111.2,
                        "active_freq_ils": True,
                        "standby_freq": 110.25,
                        "standby_freq_ils": False,
                    }
                }
            }
        }
        self.sequenceNumber += 1

        return cbor2.dumps(data)

    

def main():
    print("Starting Data Manager...")
    DSM = DisplayManager()
    DM = DataManager()
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

    while(True):
        values = DM.get_all_values()
        DSM.resetPointer()
        DSM.print_line(f"Up Time: {time.time() - start_time:.2f}s")
        DSM.print_line(f"{'DataName':<30} | {'Value':>10} | {'FPS':>10} | {'Connected':<10} | {'Status'}")
        DSM.print_line("-" * 100)
        for name, value in values.items():
            bad_val = False
            if(value is None):
                value = 0.0
                bad_val = True
            connected = "Yes" if DM.get_is_connected(name) else "No"
            fps = DM.get_fps(name)
            fps_str = f"{fps:.1f}" if fps < 1000 else f"{fps:.0f}"
            DSM.print_line(f"{name:<30} | {value:>10.2f} | {fps_str:>10} | {connected:<10} | {'BAD' if bad_val else ''}")
        
        time.sleep(0.1)

if __name__ == "__main__":
    main()
