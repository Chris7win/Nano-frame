# Nano Frame

A lightweight web interface for the **Raspberry Pi HQ Camera (IMX477)** running on **Raspberry Pi Zero W** with **Raspberry Pi OS Bookworm (32-bit)**.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![picamera2](https://img.shields.io/badge/picamera2-latest-green)
![OS](https://img.shields.io/badge/OS-Bookworm%2032bit-red)
![Camera](https://img.shields.io/badge/Camera-IMX477%20HQ-purple)

---

## Features

- Live MJPEG stream in browser (30 fps)
- Capture full resolution images (up to **4056 × 3040 / 12MP**)
- Record H264 video
- Timelapse capture with custom interval
- Real-time camera controls — brightness, contrast, saturation, sharpness, exposure, gain
- Resolution selector (640p to full 12MP)
- JPEG and PNG format support
- File manager — view and download captured files from browser
- Dark themed responsive UI

---

## Hardware Requirements

| Component | Details |
|---|---|
| Board | Raspberry Pi Zero W v1 |
| Camera | Raspberry Pi HQ Camera (IMX477) |
| Cable | 15-pin to 22-pin CSI adapter (mini ribbon) |
| Storage | microSD card 16GB+ (SanDisk recommended) |
| Power | 5V micro USB to PWR IN port |

---

## Software Requirements

| Software | Version |
|---|---|
| Raspberry Pi OS | Bookworm Lite 32-bit (Legacy) |
| Python | 3.11+ |
| picamera2 | latest |
| libcamera | 0.5.2+ |

---

## Installation

### Step 1 — Flash OS

Download and flash **Raspberry Pi OS Bookworm Lite (32-bit)** using Raspberry Pi Imager.

In Imager settings (⚙️ gear icon), configure:
- Hostname: `Give your host name`
- Username: `Give your user name`
- Password: your password
- WiFi SSID and password
- WiFi Country: your country code
- Enable SSH: ✅

### Step 2 — SSH into Pi

```bash
ssh host@user.local
# or use IP address
ssh host@192.168.x.x
```

### Step 3 — Update System

```bash
sudo apt update && sudo apt upgrade -y
```

### Step 4 — Enable Camera Overlay

```bash
sudo nano /boot/firmware/config.txt
```

Add at the bottom:
```
dtoverlay=imx477
gpu_mem=128
```

Save and reboot:
```bash
sudo reboot
```

### Step 5 — Install picamera2

```bash
sudo apt install -y python3-picamera2 --no-install-recommends
```

### Step 6 — Clone This Repository

```bash
cd ~
git clone https://github.com/Chris7win/nano-frame.git
cd nano-frame
```

### Step 7 — Run the Interface

```bash
python3 nano_frame.py
```

### Step 8 — Open in Browser

```
http://192.168.x.x:8000
```

---

## Auto-Start on Boot

To start the camera interface automatically every time the Pi boots:

```bash
sudo nano /etc/rc.local
```

Add this line before `exit 0`:
```bash
python3 /home/example/nano-frame/nano_frame.py &
```

Save and reboot. The interface will be available at port 8000 within 60 seconds of powering on.

---

## Usage

### Capture Image
1. Select resolution from dropdown (default: 1280×960, max: 4056×3040)
2. Select format (JPEG or PNG)
3. Click **Capture Image**
4. Wait 10–20 seconds (Pi Zero W is slow for full resolution)
5. File appears in Files section — click to download

### Record Video
1. Select resolution
2. Click **Start Video** — red REC badge appears
3. Click **Stop Video** when done
4. H264 file saved to `~/media/`

### Timelapse
1. Click **Timelapse**
2. Enter interval in seconds (e.g. 5)
3. Camera captures automatically at set interval
4. Click **Stop Timelapse** to end

### Camera Settings
Adjust sliders in real-time:
- **Brightness**: -1.0 to +1.0 (default 0)
- **Contrast**: 0 to 4 (default 1)
- **Saturation**: 0 to 4 (default 1)
- **Sharpness**: 0 to 16 (default 1, increase for microscopy)
- **Exposure**: Auto or manual in microseconds
- **Gain**: Auto or manual (increase for low light)

---

## File Management

All captured files are saved to `~/media/` on the Pi.

**Download via browser**: Click any filename in the Files panel.

**Download via WinSCP** (Windows):
- Host: `192.168.x.x`
- Protocol: SFTP
- Username: `example`
- Navigate to `/home/example/media/`

**Download via SCP** (Linux/Mac):
```bash
scp example@192.168.x.x:~/media/* ./downloads/
```

---

## Recommended Settings for Microscopy

| Setting | Value |
|---|---|
| Resolution | 4056×3040 (Full 12MP) |
| Format | PNG (lossless) |
| Sharpness | 8–12 |
| Saturation | 0.6–0.8 |
| Contrast | 1.2–1.5 |
| Exposure | Manual (adjust for illumination) |
| Gain | Auto or low (1–2) |

---
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `no cameras available` | Check ribbon cable orientation, add `dtoverlay=imx477` to config.txt |
| Stream not loading | Wait 60s after boot, check Pi is on same network |
| Capture takes too long | Normal on Pi Zero W — use lower resolution for preview |
| Pink/magenta image | Camera not pointed at lit scene, or missing IR cut filter |
| Server crashes on capture | Restart script: `pkill -f attox_camera.py && python3 ~/attox-camera/attox_camera.py` |
| Files not downloading | Check `~/media/` folder permissions: `chmod 755 ~/media` |

---

## Project Structure

```
nano-frame/
├── nano_frame.py    # Main application
├── README.md          # This file
└── media/             # Captured images and videos (auto-created)
```

---

## License

MIT License — free to use, modify and distribute.

---

## Credits
- [picamera2](https://github.com/raspberrypi/picamera2) — Raspberry Pi camera library
- [Raspberry Pi HQ Camera](https://www.raspberrypi.com/products/raspberry-pi-high-quality-camera/) — IMX477 sensor
