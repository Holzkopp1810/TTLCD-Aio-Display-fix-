import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path

from controller import TTLCController, State, Mode, Sensor


class TTLCGui:
    def __init__(self, root):
        self.root = root
        self.ctrl = TTLCController()

        root.title("Thermaltake LCD Control")

        # ---------- Core Buttons ----------

        self.btn_connect = tk.Button(root, text="Connect", command=self.connect)
        self.btn_disconnect = tk.Button(root, text="Disconnect", command=self.disconnect)
        self.btn_start_live = tk.Button(root, text="Start Live", command=self.start_live)
        self.btn_stop_live = tk.Button(root, text="Stop Live", command=self.stop_live)
        self.btn_wallpaper = tk.Button(root, text="Set Wallpaper", command=self.set_wallpaper)

        for b in (
            self.btn_connect,
            self.btn_disconnect,
            self.btn_start_live,
            self.btn_stop_live,
            self.btn_wallpaper,
        ):
            b.pack(fill="x", padx=4, pady=2)

        # ---------- Separator (statt Status in der Mitte) ----------
        ttk.Separator(root, orient="horizontal").pack(fill="x", padx=6, pady=8)

        # ---------- Display Mode Panel ----------
        self.mode_panel = ttk.LabelFrame(root, text="Display Mode")
        self.mode_panel.pack(fill="x", padx=6, pady=6)

        self.mode_var = tk.StringVar(value=Mode.SINGLE.value)
        self.mode_menu = ttk.OptionMenu(
            self.mode_panel,
            self.mode_var,
            Mode.SINGLE.value,
            *[m.value for m in Mode],
            command=self.change_mode,
        )
        self.mode_menu.pack(fill="x", pady=2)

        # Single-only sensor selection
        self.sensor_var = tk.StringVar(value=Sensor.CPU.value)
        self.sensor_menu = ttk.OptionMenu(
            self.mode_panel,
            self.sensor_var,
            Sensor.CPU.value,
            *[s.value for s in Sensor],
            command=self.change_sensor,
        )
        self.sensor_menu.pack(fill="x", pady=2)

        # ---------- Status (ganz unten) ----------
        ttk.Separator(root, orient="horizontal").pack(fill="x", padx=6, pady=6)
        self.status = tk.StringVar(value="Disconnected")
        tk.Label(root, textvariable=self.status).pack(fill="x", padx=6, pady=4)

        self.update_ui()
        self.tick()

    # ---------- actions ----------

    def connect(self):
        self.ctrl.connect()
        self.update_ui()

    def disconnect(self):
        self.ctrl.disconnect()
        self.update_ui()

    def start_live(self):
        self.ctrl.start_live()
        self.update_ui()

    def stop_live(self):
        self.ctrl.stop_live()
        self.update_ui()

    def set_wallpaper(self):
        p = filedialog.askopenfilename()
        if not p:
            return
        self.ctrl.set_wallpaper(Path(p))
        # UX: Wallpaper setzen => anzeigen
        if self.ctrl.state == State.CONNECTED_IDLE:
            self.ctrl.start_live()
        self.update_ui()

    def change_mode(self, value):
        self.ctrl.set_mode(Mode(value))
        # UX: Mode ändern => anzeigen (wenn connected idle)
        if self.ctrl.state == State.CONNECTED_IDLE:
            self.ctrl.start_live()
        self.update_ui()

    def change_sensor(self, value):
        self.ctrl.set_single_sensor(Sensor(value))
        if self.ctrl.state == State.CONNECTED_IDLE:
            self.ctrl.start_live()
        self.update_ui()

    # ---------- UI logic (Kindersicherung) ----------

    def update_ui(self):
        s = self.ctrl.state

        # Status-Text menschlich
        if s == State.DISCONNECTED:
            self.status.set("Disconnected")
        elif s == State.CONNECTED_IDLE:
            self.status.set("Connected (Idle)")
        else:
            self.status.set("Live active")

        # Buttons: nie „kaputt klickbar“
        self.btn_connect["state"] = tk.NORMAL if s == State.DISCONNECTED else tk.DISABLED
        self.btn_disconnect["state"] = tk.NORMAL if s == State.CONNECTED_IDLE else tk.DISABLED

        self.btn_start_live["state"] = tk.NORMAL if s == State.CONNECTED_IDLE else tk.DISABLED
        self.btn_stop_live["state"] = tk.NORMAL if s == State.LIVE else tk.DISABLED

        self.btn_wallpaper["state"] = tk.NORMAL if s != State.DISCONNECTED else tk.DISABLED

        # Mode Panel nur wenn connected oder live
        if s == State.DISCONNECTED:
            self.mode_menu["state"] = tk.DISABLED
            self.sensor_menu["state"] = tk.DISABLED
        else:
            self.mode_menu["state"] = tk.NORMAL
            # Sensor-Auswahl nur bei Single
            if self.ctrl.mode == Mode.SINGLE:
                self.sensor_menu["state"] = tk.NORMAL
            else:
                self.sensor_menu["state"] = tk.DISABLED

    # ---------- loop ----------

    def tick(self):
        self.ctrl.tick()
        self.root.after(100, self.tick)


if __name__ == "__main__":
    root = tk.Tk()
    TTLCGui(root)
    root.mainloop()
