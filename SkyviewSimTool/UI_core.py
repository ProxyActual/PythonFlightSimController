import tkinter as tk
from tkinter import ttk

try:
	from .AircraftState import AircraftState
	from .IslandNet import gen4Network
	from .IslandNet import HsiG4Dat
	from .IslandNet import AdahrsG4Dat
	from .MSFS_Connector import MSFSConnector
except ImportError:
	from AircraftState import AircraftState
	from IslandNet import gen4Network, HsiG4Dat, AdahrsG4Dat
	from MSFS_Connector import MSFSConnector

aircraft_state = AircraftState()

class AircraftStateUI(tk.Tk):
	def __init__(self):
		super().__init__()
		self.aircraft_state = aircraft_state
		self.field_vars: dict[tuple[str, str, int | None], tk.StringVar] = {}
		self.status_var = tk.StringVar()

		self.title("Aircraft State Editor")
		self.resizable(True, True)
		self.configure(padx=16, pady=16)

		self._build_ui()
		self._refresh_form()
		self._set_status("Ready.")

	def _build_ui(self) -> None:
		container = ttk.Frame(self)
		container.grid(column=0, row=0, sticky="nsew")

		sections = [
			("Air Data", "air_data", self.aircraft_state.air_data),
			("GPS Data", "gps_data", self.aircraft_state.gps_data),
			("HSI Data", "hsi_data", self.aircraft_state.hsi_data),
			("Body", "body", self.aircraft_state.body),
			("World", "world", self.aircraft_state.world),
		]

		for column, (title, section_name, values) in enumerate(sections):
			frame = ttk.LabelFrame(container, text=title, padding=10)
			frame.grid(column=column % 2, row=column // 2, sticky="nsew", padx=6, pady=6)
			self._build_section(frame, section_name, values)

		status_row = (len(sections) + 1) // 2
		ttk.Label(container, textvariable=self.status_var).grid(
			column=0, row=status_row, columnspan=2, sticky="w", padx=6, pady=(10, 0)
		)

		container.columnconfigure(0, weight=1)
		container.columnconfigure(1, weight=1)
		for row in range(status_row + 1):
			container.rowconfigure(row, weight=1 if row < status_row else 0)

		self.columnconfigure(0, weight=1)
		self.rowconfigure(0, weight=1)

	def _build_section(self, frame: ttk.LabelFrame, section_name: str, values: dict) -> None:
		row = 0
		for field_name, value in values.items():
			if isinstance(value, list):
				label_text = f"{field_name}:"
				if section_name == "air_data" and field_name == "p_alt":
					label_text = "p_alt (ft):"

				ttk.Label(frame, text=label_text).grid(
					column=0, row=row, sticky="w", padx=(0, 8), pady=4
				)
				for index, _ in enumerate(value):
					entry = ttk.Entry(
						frame,
						textvariable=self._get_field_var(section_name, field_name, index),
						width=10,
					)
					entry.grid(column=index + 1, row=row, sticky="ew", padx=2, pady=4)
					entry.bind("<Return>", self.apply_state)
					entry.bind("<KP_Enter>", self.apply_state)
			else:
				label_text = f"{field_name}:"
				if section_name == "air_data" and field_name == "p_alt":
					label_text = "p_alt (ft):"

				ttk.Label(frame, text=label_text).grid(
					column=0, row=row, sticky="w", padx=(0, 8), pady=4
				)
				entry = ttk.Entry(
					frame,
					textvariable=self._get_field_var(section_name, field_name, None),
					width=12,
				)
				entry.grid(column=1, row=row, columnspan=3, sticky="ew", pady=4)
				entry.bind("<Return>", self.apply_state)
				entry.bind("<KP_Enter>", self.apply_state)
			row += 1

		for column in range(4):
			frame.columnconfigure(column, weight=1 if column > 0 else 0)

	def _get_field_var(self, section_name: str, field_name: str, index: int | None) -> tk.StringVar:
		key = (section_name, field_name, index)
		if key not in self.field_vars:
			self.field_vars[key] = tk.StringVar()
		return self.field_vars[key]

	def _refresh_form(self) -> None:
		for section_name in ("air_data", "gps_data", "hsi_data", "body", "world"):
			section = getattr(self.aircraft_state, section_name)
			for field_name, value in section.items():
				if isinstance(value, list):
					for index, item in enumerate(value):
						self._get_field_var(section_name, field_name, index).set(
							self._format_value(section_name, field_name, item)
						)
				else:
					self._get_field_var(section_name, field_name, None).set(
						self._format_value(section_name, field_name, value)
					)

	def _format_value(self, section_name: str, field_name: str, value: float) -> str:
		if section_name == "air_data" and field_name == "p_alt":
			return f"{float(value) * 3.28084:.3f}"
		return f"{float(value):.3f}"

	def _parse_value(self, section_name: str, field_name: str, raw_value: str) -> float:
		parsed = float(raw_value)
		if section_name == "air_data" and field_name == "p_alt":
			return parsed * 0.3048
		return parsed

	def apply_state(self, _event: tk.Event | None = None) -> None:
		try:
			for section_name in ("air_data", "gps_data", "hsi_data", "body", "world"):
				section = getattr(self.aircraft_state, section_name)
				for field_name, value in section.items():
					if isinstance(value, list):
						updated_values = []
						for index in range(len(value)):
							raw_value = self._get_field_var(section_name, field_name, index).get()
							updated_values.append(
								self._parse_value(section_name, field_name, raw_value)
							)
						section[field_name] = updated_values
					else:
						raw_value = self._get_field_var(section_name, field_name, None).get()
						section[field_name] = self._parse_value(section_name, field_name, raw_value)
		except ValueError as error:
			self._set_status(f"Enter valid numeric values. {error}")
			return

		self._refresh_form()
		self._set_status("Aircraft state updated.")

	def _set_status(self, message: str) -> None:
		self.status_var.set(message)



def launch_aircraft_state_ui() -> AircraftState:
	app = AircraftStateUI()
	app.mainloop()
	return app.aircraft_state

if __name__ == "__main__":
	gen4_network = gen4Network()
	msfs_connector = MSFSConnector(aircraft_state)
	hsi_g4_dat = HsiG4Dat(gen4_network.sock, aircraft_state)
	adahrs_g4_dat = AdahrsG4Dat(gen4_network.sock, aircraft_state)
	launch_aircraft_state_ui()
