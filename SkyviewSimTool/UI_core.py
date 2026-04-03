import tkinter as tk
from tkinter import ttk
import threading
import time

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
		self.bool_vars: dict[tuple[str, str], tk.BooleanVar] = {}
		self.bool_checkboxes: dict[tuple[str, str], tk.Checkbutton] = {}
		self.bool_default_fg: dict[tuple[str, str], str] = {}
		self.status_var = tk.StringVar()
		self.style = ttk.Style(self)

		self.title("Aircraft State Solution")
		self.resizable(True, True)
		self.configure(padx=16, pady=16)
		self._init_styles()

		self._build_ui()
		self._refresh_form()
		self._set_status("Ready.")

		self._start_auto_refresh()
		self.protocol("WM_DELETE_WINDOW", self._on_closing)

	def _init_styles(self) -> None:
		self.style.configure("StateEditor.TEntry")
		self.style.configure("StateEditor.Active.TEntry", fieldbackground="#b9f6ca")

	def _build_ui(self) -> None:
		container = ttk.Frame(self)
		container.grid(column=0, row=0, sticky="nsew")

		sections = [
			("Air Data", "air_data", self.aircraft_state.air_data),
			("GPS Data", "gps_data", self.aircraft_state.gps_data),
			("HSI Data", "hsi_data", self.aircraft_state.hsi_data),
			("Sim State", "sim_state", self.aircraft_state.sim_state),
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
			if isinstance(value, bool):
				key = (section_name, field_name)
				bool_var = tk.BooleanVar(value=value)
				self.bool_vars[key] = bool_var
				cb = tk.Checkbutton(
					frame,
					text=f"{field_name}",
					variable=bool_var,
					onvalue=True,
					offvalue=False,
					selectcolor="#ffffff",
					command=lambda sn=section_name, fn=field_name: self._on_bool_toggle(sn, fn),
				)
				self.bool_checkboxes[key] = cb
				self.bool_default_fg[key] = cb.cget("fg")
				self._set_bool_checkbox_style(key)
				cb.grid(column=0, row=row, columnspan=4, sticky="w", pady=4)
				row += 1
				continue
			if isinstance(value, list):
				label_text = f"{field_name}:"
				if section_name == "air_data" and field_name == "p_alt":
					label_text = "p_alt (ft):"
				if section_name == "gps_data" and field_name == "alt":
					label_text = "alt (ft):"

				ttk.Label(frame, text=label_text).grid(
					column=0, row=row, sticky="w", padx=(0, 8), pady=4
				)
				for index, _ in enumerate(value):
					entry = ttk.Entry(
						frame,
						textvariable=self._get_field_var(section_name, field_name, index),
						style="StateEditor.TEntry",
						width=10,
					)
					entry.grid(column=index + 1, row=row, sticky="ew", padx=2, pady=4)
					entry.bind("<Return>", self.apply_state)
					entry.bind("<KP_Enter>", self.apply_state)
					entry.bind("<FocusIn>", self._set_entry_active)
					entry.bind("<FocusOut>", self._set_entry_inactive)
			else:
				label_text = f"{field_name}:"
				if section_name == "air_data" and field_name == "p_alt":
					label_text = "p_alt (ft):"
				if section_name == "gps_data" and field_name == "alt":
					label_text = "alt (ft):"

				ttk.Label(frame, text=label_text).grid(
					column=0, row=row, sticky="w", padx=(0, 8), pady=4
				)
				entry = ttk.Entry(
					frame,
					textvariable=self._get_field_var(section_name, field_name, None),
					style="StateEditor.TEntry",
					width=12,
				)
				entry.grid(column=1, row=row, columnspan=3, sticky="ew", pady=4)
				entry.bind("<Return>", self.apply_state)
				entry.bind("<KP_Enter>", self.apply_state)
				entry.bind("<FocusIn>", self._set_entry_active)
				entry.bind("<FocusOut>", self._set_entry_inactive)
			row += 1

		for column in range(4):
			frame.columnconfigure(column, weight=1 if column > 0 else 0)

	def _get_field_var(self, section_name: str, field_name: str, index: int | None) -> tk.StringVar:
		key = (section_name, field_name, index)
		if key not in self.field_vars:
			self.field_vars[key] = tk.StringVar()
		return self.field_vars[key]

	def _refresh_form(self) -> None:
		for section_name in ("air_data", "gps_data", "hsi_data", "sim_state", "body", "world"):
			section = getattr(self.aircraft_state, section_name)
			for field_name, value in section.items():
				if isinstance(value, bool):
					key = (section_name, field_name)
					if key in self.bool_vars:
						self.bool_vars[key].set(value)
						self._set_bool_checkbox_style(key)
				elif isinstance(value, list):
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
			for section_name in ("air_data", "gps_data", "hsi_data", "sim_state", "body", "world"):
				section = getattr(self.aircraft_state, section_name)
				for field_name, value in section.items():
					if isinstance(value, bool):
						continue
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

	def _on_bool_toggle(self, section_name: str, field_name: str) -> None:
		key = (section_name, field_name)
		value = self.bool_vars[key].get()
		getattr(self.aircraft_state, section_name)[field_name] = value
		self._set_bool_checkbox_style(key)

	def _set_bool_checkbox_style(self, key: tuple[str, str]) -> None:
		if key not in self.bool_checkboxes or key not in self.bool_vars:
			return
		checkbox = self.bool_checkboxes[key]
		default_fg = self.bool_default_fg.get(key, checkbox.cget("fg"))
		if self.bool_vars[key].get():
			checkbox.configure(selectcolor="#00cc44", fg=default_fg, activeforeground=default_fg)
		else:
			checkbox.configure(selectcolor="#ffffff", fg=default_fg, activeforeground=default_fg)

	def _set_entry_active(self, event: tk.Event) -> None:
		if isinstance(event.widget, ttk.Entry):
			event.widget.configure(style="StateEditor.Active.TEntry")

	def _set_entry_inactive(self, event: tk.Event) -> None:
		if isinstance(event.widget, ttk.Entry):
			event.widget.configure(style="StateEditor.TEntry")

	def _start_auto_refresh(self) -> None:
		self._refresh_thread = threading.Thread(target=self._auto_refresh_loop, daemon=True)
		self._refresh_thread.start()

	def _auto_refresh_loop(self) -> None:
		while True:
			try:
				time.sleep(0.1)
				self.after(0, self._refresh_form_live)
			except Exception:
				break

	def _refresh_form_live(self) -> None:
		try:
			focus_widget = self.focus_get()
			focused_field_key = None
			if isinstance(focus_widget, ttk.Entry):
				for key, var in self.field_vars.items():
					if focus_widget.cget("textvariable") == str(var):
						focused_field_key = key
						break

			for section_name in ("air_data", "gps_data", "hsi_data", "sim_state", "body", "world"):
				section = getattr(self.aircraft_state, section_name)
				for field_name, value in section.items():
					if isinstance(value, bool):
						bool_key = (section_name, field_name)
						if bool_key in self.bool_vars:
							if self.bool_vars[bool_key].get() != value:
								self.bool_vars[bool_key].set(value)
								self._set_bool_checkbox_style(bool_key)
					elif isinstance(value, list):
						for index, item in enumerate(value):
							key = (section_name, field_name, index)
							if key != focused_field_key:
								var = self._get_field_var(section_name, field_name, index)
								formatted = self._format_value(section_name, field_name, item)
								if var.get() != formatted:
									var.set(formatted)
					else:
						key = (section_name, field_name, None)
						if key != focused_field_key:
							var = self._get_field_var(section_name, field_name, None)
							formatted = self._format_value(section_name, field_name, value)
							if var.get() != formatted:
								var.set(formatted)
		except Exception:
			pass

	def _on_closing(self) -> None:
		self.destroy()



def launch_aircraft_state_ui() -> AircraftState:
	app = AircraftStateUI()
	app.mainloop()
	return app.aircraft_state

def start_rough_sim_worker(state: AircraftState) -> threading.Thread:
	def _run() -> None:
		while True:
			try:
				state.roughSim()
			except Exception:
				pass
			time.sleep(0.05)

	worker = threading.Thread(target=_run, daemon=True)
	worker.start()
	return worker

if __name__ == "__main__":
	gen4_network = gen4Network()
	msfs_connector = MSFSConnector(aircraft_state)
	hsi_g4_dat = HsiG4Dat(gen4_network.sock, aircraft_state)
	adahrs_g4_dat = AdahrsG4Dat(gen4_network.sock, aircraft_state)
	rough_sim_worker = start_rough_sim_worker(aircraft_state)
	launch_aircraft_state_ui()
