# TTLCD-Aio-Display-fix-



# Thermaltake TT LCD (TH V2 Ultra) – Linux Control / Reverse Engineering

Working standalone control software for the Thermaltake TH V2 Ultra LCD display on Linux.

This project provides a fully functional Python-based implementation for driving the circular LCD via USB, including live image streaming, layouts, and basic sensor integration.

---

## ⚠️ Status

**WORK IN PROGRESS – but functional**

* ✔ Display communication works
* ✔ Live image streaming works
* ✔ Multiple layouts implemented
* ✔ GUI working
* ⚠ Sensors partially implemented
* ❌ Not an OpenRGB plugin (yet)

---

## 🧠 Background

The Thermaltake LCD is **not officially supported on Linux**.

This project is based on:

* reverse engineering USB communication
* analyzing device behavior
* rebuilding the protocol in Python

The display:

* accepts JPEG frames
* requires chunked USB transfers
* needs periodic keepalive packets

---

## 🔧 Hardware

* Device: Thermaltake TH V2 Ultra LCD
* USB VID: `0x264A`
* USB PID: `0x233C`

### Endpoints

| Endpoint | Type | Purpose      |
| -------- | ---- | ------------ |
| 0x01     | OUT  | Commands     |
| 0x03     | OUT  | Frame stream |
| 0x84     | IN   | ACK          |

---

## 🧱 Architecture

The project is split into three main parts:

### 1. `engine.py` – Hardware Layer

Handles:

* USB communication (pyusb)
* command packets
* JPEG preparation
* frame chunking (1020 bytes per chunk)
* keepalive system

This is the **core reverse engineered part**.

---

### 2. `controller.py` – Logic Layer

Handles:

* state machine (DISCONNECTED / LIVE)
* rendering
* layout logic
* sensor access
* wallpaper handling

This is the **application brain**.

---

### 3. `ttlcd_gui.py` – GUI

* built with tkinter
* safe UI (no invalid states)
* connect / disconnect
* start / stop live
* wallpaper selection
* mode switching

---

## 🖥 Features

### Live Display

* continuous JPEG streaming
* adjustable FPS
* automatic keepalive

### Layouts

* Single (one sensor)
* Quad Cross
* Quad Quadrant

### Wallpaper

* background image support
* auto-fit to 480×480

### Rendering

* dynamic text placement
* font scaling
* layout-specific tuning

---

## 🌡 Sensors

Current state:

| Sensor | Status                          |
| ------ | ------------------------------- |
| CPU    | ✔ working (via `sensors`, Tctl) |
| GPU    | ⚠ placeholder                   |
| Liquid | ⚠ not implemented               |

Example:

```bash
sensors
```

Used to parse CPU temperature.

---

## 🚀 Usage

Run the GUI:

```bash
python ttlcd_gui.py
```

Steps:

1. Connect device
2. Start Live mode
3. Select layout
4. (Optional) set wallpaper

---

## 📦 Dependencies

* Python 3.10+
* pyusb
* pillow
* lm-sensors (for CPU temp)

Install:

```bash
pip install pyusb pillow
```

---

## ⚙️ How it works

### Image Pipeline

1. Render frame (PIL)
2. Resize to 480×480
3. Encode JPEG
4. Ensure size < ~30KB
5. Split into 30 chunks
6. Send via USB endpoint 0x03

### Keepalive

Device requires periodic command packets to stay in "live mode".

Without keepalive:

* display returns to standby
* firmware takes over again

---

## ⚠️ Known Limitations

* GPU temperature not implemented
* Liquid temperature not accessible yet
* no persistence (display resets on disconnect)
* Linux support is unofficial workaround

---

## 🔮 Planned Features

### Short term

* proper GPU sensor integration
* improve sensor abstraction

### Mid term

* convert to OpenRGB plugin
* integrate OpenRGB sensor data

### Long term (experimental / risky)

* inject custom standby image into firmware
* persistent display configuration

---

## 🧊 Stability Notes

* stable during continuous streaming
* relies on correct USB timing
* may break with kernel / USB changes

---

## 💡 Design Philosophy

* keep architecture simple
* avoid overengineering
* prioritize functionality over visuals
* prevent invalid UI states ("idiot-proof")

---

## 🧪 Disclaimer

This is a reverse engineered implementation.

* not officially supported by Thermaltake
* may break with updates
* use at your own risk

---

## 👤 Author

Holzkopp1810

---

## 🎯 Goal

Provide a working Linux solution for a device that otherwise requires proprietary Windows software.

---
