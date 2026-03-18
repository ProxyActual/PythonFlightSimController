import tkinter as tk
from tkinter import ttk
from SimConnection import *

class FlightSimUI:
    DM = DataManager()
    G4n = gen4Network()

    def __init__(self, root):
        width = 800
        height = 600

        self.root = root
        self.root.title("Flight Simulator Controller")
        self.root.geometry(f"{width}x{height}")

        self.start_button_adahrs = ttk.Button(self.root, text="ADAHRS", command=self.start_simulation_adahrs)
        self.start_button_adahrs.pack(pady=20)
        self.start_button_adahrs.place(x=10, y=10)

        self.start_button_hsi = ttk.Button(self.root, text="HSI", command=self.start_simulation_hsi)
        self.start_button_hsi.pack(pady=20)

    def start_simulation_adahrs(self):
        self.adahrs_sim = AdahrsSim(self.DM, self.G4n.sock)

    def start_simulation_hsi(self):
        self.hsi_sim = HsiSim(self.DM, self.G4n.sock)


if __name__ == "__main__":
    root = tk.Tk()
    app = FlightSimUI(root)
    root.mainloop()

    