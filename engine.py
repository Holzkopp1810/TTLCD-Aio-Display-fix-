# engine.py
# Hardware-Engine für Thermaltake LCD

import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import usb.core
import usb.util
from PIL import Image, ImageOps

VID = 0x264A
PID = 0x233C

EP_CMD_OUT   = 0x01
EP_FRAME_OUT = 0x03
EP_ACK_IN    = 0x84

CMD_PACKET_SIZE = 440
CMD_PAYLOAD_SIZE = 436

FRAME_HEADER_SIZE = 4
FRAME_PAYLOAD_SIZE = 1020
LIVE_CHUNKS = 30
LIVE_MAX_JPEG_BYTES = LIVE_CHUNKS * FRAME_PAYLOAD_SIZE

DISPLAY_SIZE = (480, 480)


@dataclass
class EngineConfig:
    rotation_deg: int = 0
    fps: float = 1.0
    keepalive_s: float = 1.0
    usb_timeout_ms: int = 1000
    chunk_delay_ms: float = 1.0


class TTLCDEngine:
    def __init__(self, cfg: EngineConfig):
        self.cfg = cfg
        self.dev = None
        self.last_keepalive = 0.0

    # ---------- lifecycle ----------

    def connect(self):
        self.dev = usb.core.find(idVendor=VID, idProduct=PID)
        if self.dev is None:
            raise RuntimeError("Device not found")

        for iface in (0, 1):
            try:
                if self.dev.is_kernel_driver_active(iface):
                    self.dev.detach_kernel_driver(iface)
            except Exception:
                pass

        self.dev.set_configuration()
        for iface in (0, 1):
            try:
                usb.util.claim_interface(self.dev, iface)
            except Exception:
                pass

        self._init_live()

    def disconnect(self):
        time.sleep(0.6)  # passive linger
        try:
            usb.util.dispose_resources(self.dev)
        except Exception:
            pass
        self.dev = None

    # ---------- USB helpers ----------

    def _send_cmd(self, cmd: int, payload: bytes = b""):
        pkt = bytearray(CMD_PACKET_SIZE)
        pkt[0] = cmd & 0xFF
        pkt[3] = 0x80
        if payload:
            pkt[4:4 + len(payload)] = payload
        self.dev.write(EP_CMD_OUT, pkt, timeout=self.cfg.usb_timeout_ms)

    def _drain_ack(self):
        for _ in range(8):
            try:
                self.dev.read(EP_ACK_IN, 16, timeout=1)
            except Exception:
                break

    # ---------- live ----------

    def _init_live(self):
        for c in (0x85, 0x85, 0x87, 0x87, 0x84, 0x84, 0x81, 0x81):
            self._send_cmd(c)

        payload = (0x64).to_bytes(4, "little") + b"\x00" * (CMD_PAYLOAD_SIZE - 4)
        self._send_cmd(0x12, payload)

    def keepalive(self):
        now = time.time()
        if now - self.last_keepalive >= self.cfg.keepalive_s:
            payload = (0x64).to_bytes(4, "little") + b"\x00" * (CMD_PAYLOAD_SIZE - 4)
            self._send_cmd(0x12, payload)
            self.last_keepalive = now

    # ---------- image ----------

    def prepare_image(self, path: Path) -> bytes:
        with Image.open(path) as img:
            try:
                img.seek(0)
            except Exception:
                pass

            img = img.convert("RGB")
            img = ImageOps.fit(
                img,
                DISPLAY_SIZE,
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )

            if self.cfg.rotation_deg:
                img = img.rotate(self.cfg.rotation_deg, expand=False)

        from io import BytesIO
        for q in [92, 88, 84, 80, 76, 72, 68, 64, 60]:
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=q, optimize=True)
            data = buf.getvalue()
            if len(data) <= LIVE_MAX_JPEG_BYTES:
                return data

        raise RuntimeError("Image too large")

    def show_image(self, jpeg: bytes):
        padded = jpeg + b"\x00" * (LIVE_MAX_JPEG_BYTES - len(jpeg))
        delay = self.cfg.chunk_delay_ms / 1000.0

        for i in range(LIVE_CHUNKS):
            hdr = bytearray(4)
            hdr[0] = 0x08
            hdr[1] = LIVE_CHUNKS if i == 0 else i
            hdr[3] = 0x80 if i == 0 else 0x00

            chunk = padded[i * FRAME_PAYLOAD_SIZE:(i + 1) * FRAME_PAYLOAD_SIZE]
            self.dev.write(EP_FRAME_OUT, bytes(hdr) + chunk, timeout=self.cfg.usb_timeout_ms)
            self._drain_ack()
            if delay:
                time.sleep(delay)
