
import time
import threading
import cbor2
from SimConnect import *

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
        while self.is_running:
            # Check if the thread is safe to run
            value = 0
            if(self.simConnected):
                value = self.aq.get(self.dataTarget)
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

class MSFSConnector:
    def __init__(self, aircraft_state):
        self.aircraft_state = aircraft_state
        self.data_manager = DataManager()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def convert_to_degrees(self, value):
        return value * (180.0 / 3.141592653589793)

    def run(self):
        while True:
            if(self.data_manager.get_is_connected("PLANE_HEADING_DEGREES_TRUE")):
                self.aircraft_state.body["xyz_rate"] = [
                    self.convert_to_degrees(self.data_manager.get_value_safe("ROTATION_VELOCITY_BODY_X")),
                    self.convert_to_degrees(self.data_manager.get_value_safe("ROTATION_VELOCITY_BODY_Y")),
                    self.convert_to_degrees(self.data_manager.get_value_safe("ROTATION_VELOCITY_BODY_Z"))
                ]
                self.aircraft_state.body["xyz_accel"] = [
                    0.0,
                    -self.data_manager.get_value_safe("TURN_COORDINATOR_BALL") * -.3,
                    -self.data_manager.get_value_safe("G_FORCE")
                ]
                self.aircraft_state.world["ypr"] = [
                    self.convert_to_degrees(self.data_manager.get_value_safe("GPS_GROUND_MAGNETIC_TRACK")),
                    self.convert_to_degrees(self.data_manager.get_value_safe("PLANE_PITCH_DEGREES")),
                    self.convert_to_degrees(self.data_manager.get_value_safe("PLANE_BANK_DEGREES"))
                ]
                self.aircraft_state.air_data["p_alt"] = self.data_manager.get_value_safe("PRESSURE_ALTITUDE")
                self.aircraft_state.air_data["vs"] = self.data_manager.get_value_safe("VERTICAL_SPEED")
                self.aircraft_state.air_data["ias"] = self.data_manager.get_value_safe("AIRSPEED_INDICATED")
                #self.aircraft_state.air_data["tas"] = this is not used by sv
                self.aircraft_state.air_data["aoa"] = self.data_manager.get_value_safe("INCIDENT_ALPHA")
                self.aircraft_state.air_data["oat"] = self.data_manager.get_value_safe("STANDARD_ATM_TEMPERATURE") - 460.0

                self.aircraft_state.gps_data["lat"] = self.data_manager.get_value_safe("PLANE_LATITUDE")
                self.aircraft_state.gps_data["lon"] = self.data_manager.get_value_safe("PLANE_LONGITUDE")
                self.aircraft_state.gps_data["alt"] = self.data_manager.get_value_safe("PRESSURE_ALTITUDE")
                self.aircraft_state.gps_data["gndtrk"] = self.convert_to_degrees(self.data_manager.get_value_safe("GPS_GROUND_MAGNETIC_TRACK"))

                self.aircraft_state.hsi_data["crs_dev"] = self.data_manager.get_value_safe("NAV_CDI:1")
                self.aircraft_state.hsi_data["gsi_deflection"] = self.data_manager.get_value_safe("HSI_GSI_NEEDLE")