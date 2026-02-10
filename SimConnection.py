
from SimConnect import *
from time import *
import threading
import socket

class DataThread:
    value = 0
    is_running = True
    simConnected = False
    last_update = time()
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
            value = self.value + .00001  # Add a small random value to simulate changes
            if(self.simConnected):
                value = self.aq.get(self.dataTarget)
            
            self.ValLock.acquire()
            self.value = value
            self.ValLock.release()

            delta = time() - self.last_update
            # Avoid divide by zero if the update is too fast
            while delta == 0:
                delta = time() - self.last_update
            self.timeLock.acquire()
            self.fps = 1 / delta
            self.timeLock.release()
            self.last_update = time()
    
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
    valuesLock = threading.Lock()
    values = {}

    def __init__(self):
        pass

    def addValue(self, name):
        self.valuesLock.acquire()
        if name not in self.values:
            self.values[name] = DataThread(name)
        self.valuesLock.release()

    def get_value(self, name):
        self.addValue(name)
        return self.values[name].get_value()

    def get_fps(self, name):
        self.addValue(name)
        return self.values[name].get_fps()

    def get_is_connected(self, name):
        self.addValue(name)
        return self.values[name].get_is_connected()
    
    def get_all_values(self):
        self.valuesLock.acquire()
        all_values = {name: thread.get_value() for name, thread in self.values.items()}
        self.valuesLock.release()
        return all_values

class UDPServerThread:
    def __init__(self, data_manager, host='0.0.0.0', port=5005):
        self.data_manager = data_manager
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        self.running = True
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                request = data.decode().strip()
                if request:
                    value = self.data_manager.get_value(request)
                    response = str(value).encode()
                    self.sock.sendto(response, addr)
            except Exception:
                continue


class DisplayManager:
    lineCount = 0

    def __init__(self):
        pass

    def print_line(self, text):
        print("\033[K" + text)
        self.lineCount += 1
    
    def resetPointer(self):
        for _ in range(self.lineCount):
            print("\033[F", end="")
        self.lineCount = 0

DSM = DisplayManager()
DM = DataManager()
start_time = time()


udp_server = UDPServerThread(DM)


while(start_time - time() < 10):
    values = DM.get_all_values()
    DSM.resetPointer()

    for name, value in values.items():
        DSM.print_line(f"{name}: {value:.2f} | FPS: {DM.get_fps(name):.2f} | Connected: {DM.get_is_connected(name)}")
    
    sleep(0.1)
