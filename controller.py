from pathlib import Path
import subprocess
import time
from enum import Enum, auto

from PIL import Image, ImageDraw, ImageFont, ImageOps
from engine import TTLCDEngine, EngineConfig


class State(Enum):
    DISCONNECTED = auto()
    CONNECTED_IDLE = auto()
    LIVE = auto()


class Mode(Enum):
    SINGLE = "Single Temp"
    QUAD_CROSS = "Quad (Cross)"
    QUAD_QUADRANT = "Quad (Quadrant)"


class Sensor(Enum):
    CPU = "CPU"
    GPU = "GPU"
    LIQUID = "Liq Temp"


class TTLCController:
    def __init__(self):
        self.cfg = EngineConfig(rotation_deg=180, fps=8.0)
        self.engine = TTLCDEngine(self.cfg)

        self.state = State.DISCONNECTED
        self.mode = Mode.QUAD_CROSS
        self.single_sensor = Sensor.CPU

        self.wallpaper_path: Path | None = None
        self.last_render = 0.0

    # ---------- lifecycle ----------

    def connect(self):
        if self.state != State.DISCONNECTED:
            return
        self.engine.connect()
        self.state = State.CONNECTED_IDLE

    def disconnect(self):
        if self.state != State.CONNECTED_IDLE:
            return
        time.sleep(0.2)
        self.engine.disconnect()
        self.state = State.DISCONNECTED

    def start_live(self):
        if self.state != State.CONNECTED_IDLE:
            return
        self.last_render = 0.0
        self.state = State.LIVE

    def stop_live(self):
        if self.state == State.LIVE:
            self.state = State.CONNECTED_IDLE

    # ---------- config ----------

    def set_mode(self, mode: Mode):
        self.mode = mode

    def set_wallpaper(self, path: Path):
        self.wallpaper_path = Path(path)

    # ---------- sensors ----------

    def get_sensor_value(self, sensor: Sensor) -> float:
        if sensor == Sensor.CPU:
            out = subprocess.check_output(["sensors"], text=True)
            for line in out.splitlines():
                if "Tctl:" in line:
                    return float(line.split("+")[1].split("°")[0])
        return 42.0

    # ---------- helpers ----------

    @staticmethod
    def _center(draw, text, font, cx, cy):
        b = draw.textbbox((0, 0), text, font=font)
        return cx - (b[2] - b[0]) // 2, cy - (b[3] - b[1]) // 2

    # ---------- rendering ----------

    def render_frame(self):
        size = (480, 480)

        if self.wallpaper_path and self.wallpaper_path.exists():
            img = Image.open(self.wallpaper_path).convert("RGB")
            img = ImageOps.fit(img, size, Image.Resampling.LANCZOS)
        else:
            img = Image.new("RGB", size, (0, 0, 0))

        draw = ImageDraw.Draw(img)

        try:
            # BASE
            font_cross_value = ImageFont.truetype("DejaVuSans-Bold.ttf", 48)
            font_cross_label = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)

            # QUADRANT tweaks
            font_quad_label = ImageFont.truetype("DejaVuSans-Bold.ttf", int(36 * 1.10))   # +10%
            font_quad_value = ImageFont.truetype("DejaVuSans-Bold.ttf", int(48 * 0.85))   # -15%
        except Exception:
            font_cross_value = font_cross_label = font_quad_label = font_quad_value = ImageFont.load_default()

        line_color = (170, 170, 170)
        label_color = (215, 215, 215)
        value_color = (255, 255, 255)

        # ---------- QUAD CROSS (FINAL GEOMETRY) ----------
        if self.mode == Mode.QUAD_CROSS:
            slots = [
                (Sensor.CPU,     (240, 105)),
                (Sensor.GPU,     (375, 240)),
                (Sensor.LIQUID,  (240, 375)),
                (Sensor.CPU,     (105, 240)),
            ]

            for sensor, (cx, cy) in slots:
                val = self.get_sensor_value(sensor)
                label = sensor.value
                value = f"{val:.1f}°C"

                lx, ly = self._center(draw, label, font_cross_label, cx, cy - 28)
                vx, vy = self._center(draw, value, font_cross_value, cx, cy + 22)

                draw.text((lx, ly), label, fill=label_color, font=font_cross_label)
                draw.text((vx, vy), value, fill=value_color, font=font_cross_value)

            # Horizontal: komplett durchgehend
            draw.line((40, 240, 440, 240), fill=line_color, width=2)

            # Vertical: NUR zentrales Segment (3x Länge), keine Randsegmente
            draw.line((240, 180, 240, 300), fill=line_color, width=2)

        # ---------- QUAD QUADRANT (FINAL TUNING) ----------
        elif self.mode == Mode.QUAD_QUADRANT:
            items = [
                (Sensor.CPU,     (135, 135)),
                (Sensor.GPU,     (345, 135)),
                (Sensor.LIQUID,  (345, 345)),
                (Sensor.CPU,     (135, 345)),
            ]

            # Kreuz vollständig (schneidet nichts)
            draw.line((40, 240, 440, 240), fill=line_color, width=2)
            draw.line((240, 40, 240, 440), fill=line_color, width=2)

            for sensor, (cx, cy) in items:
                val = self.get_sensor_value(sensor)
                label = sensor.value
                value = f"{val:.1f}°C"

                # weiter vom Kreuz weg
                lx, ly = self._center(draw, label, font_quad_label, cx, cy - 30)
                vx, vy = self._center(draw, value, font_quad_value, cx, cy + 26)

                draw.text((lx, ly), label, fill=label_color, font=font_quad_label)
                draw.text((vx, vy), value, fill=value_color, font=font_quad_value)

        path = Path("/tmp/ttlcd_live.jpg")
        img.save(path, "JPEG", quality=90)
        return path

    # ---------- tick ----------

    def tick(self):
        if self.state != State.LIVE:
            return

        self.engine.keepalive()
        now = time.time()

        if now - self.last_render >= 1.0 / self.cfg.fps:
            jpeg = self.engine.prepare_image(self.render_frame())
            self.engine.show_image(jpeg)
            self.last_render = now
