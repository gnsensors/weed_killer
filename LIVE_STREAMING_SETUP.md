# Live Streaming Setup Guide

Use your Android phone as a wireless camera for real-time weed detection.

---

## Quick Start (5 minutes)

### 1. Install IP Camera App on Phone

**Recommended App:** "IP Webcam" (free on Google Play Store)

- Open Google Play Store
- Search for "IP Webcam"
- Install the app by Pavel Khlebovich

**Alternative apps:**
- DroidCam
- Camera Stream
- IP Camera Lite

### 2. Setup Phone Camera

1. **Open IP Webcam app**
2. **Scroll down and tap "Start server"**
3. **Note the URL shown** (e.g., `http://192.168.1.100:8080`)
4. **Keep phone plugged in** (streaming drains battery)
5. **Optional:** Adjust video settings:
   - Resolution: 1080p or 720p
   - Quality: Medium or High
   - FPS limit: 30

### 3. Run Detection on Computer

**Option A: Auto-discover camera**
```bash
source venv/bin/activate
python3 live_stream_detector.py --quick
```

**Option B: Manual URL entry**
```bash
source venv/bin/activate
python3 live_stream_detector.py --url http://192.168.1.100:8080/video
```

**Option C: Interactive discovery**
```bash
source venv/bin/activate
python3 live_stream_detector.py --discover
```

---

## Detailed Setup

### Phone Setup

#### IP Webcam App Configuration

1. **Video Preferences**
   - Video resolution: `1280x720` (good balance of quality/performance)
   - Video quality: `70%`
   - Video orientation: `Landscape`
   - FPS limit: `30`

2. **Local Broadcasting**
   - Port: `8080` (default)
   - Enable: `Start on boot` (optional)
   - Enable: `Prevent phone from sleeping`

3. **Starting the Server**
   - Scroll to bottom of main screen
   - Tap "Start server"
   - App shows URL like: `http://192.168.1.100:8080`
   - Leave app running (can lock screen if "prevent sleep" enabled)

4. **Testing in Browser**
   - On computer, open browser
   - Go to: `http://<phone-ip>:8080`
   - You should see video feed
   - Try: `http://<phone-ip>:8080/video` for direct stream

### Computer Setup

#### Install Dependencies

If you haven't already installed requests:

```bash
source venv/bin/activate
pip install requests
```

Or reinstall all dependencies:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

#### Test Connection

Test if you can reach the phone:

```bash
source venv/bin/activate
python3 stream_manager.py http://192.168.1.100:8080/video
```

Should output:
```
✓ URL is reachable
✓ Connected successfully
  Resolution: 1280x720
  FPS: 30.0
```

---

## Usage Examples

### Basic Live Detection

```bash
python3 live_stream_detector.py --url http://192.168.1.100:8080/video
```

**What you'll see:**
- Live video with green boxes around detected weeds
- FPS counter (target: 15-30 fps)
- Latency indicator
- Weed count per frame
- Status indicator (green = good performance)

**Controls:**
- **Q** - Quit
- **S** - Save current detection settings
- **X** (close window) - Quit

### Network Discovery

If you don't know your phone's IP address:

```bash
# Quick scan (fast)
python3 live_stream_detector.py --quick

# Full scan (slower, more thorough)
python3 live_stream_detector.py --discover
```

### Headless Mode (SSH/Remote)

Run without display (for remote server):

```bash
python3 live_stream_detector.py --url http://192.168.1.100:8080/video --headless
```

Stats printed to console every 100 frames.

### Using Saved Detection Settings

If you've tuned parameters with `video_tuner_v2.py`:

```bash
# First, tune parameters on a test video
python3 video_tuner_v2.py test_video.mp4
# Press 'P' to save settings

# Then use those settings for live detection
python3 live_stream_detector.py --url http://192.168.1.100:8080/video
# Settings automatically loaded from weed_detector_config.json
```

---

## Troubleshooting

### Can't Connect to Stream

**Problem:** "Failed to connect to stream"

**Solutions:**

1. **Check same WiFi network**
   ```bash
   # On computer
   ip addr show  # Linux
   ifconfig      # Mac
   ipconfig      # Windows

   # Should be same 192.168.x.x range as phone
   ```

2. **Verify phone IP address**
   - On phone: Settings → About Phone → Status → IP address
   - Should match IP in URL

3. **Test in browser first**
   - Open `http://<phone-ip>:8080` in browser
   - Should see camera interface
   - Try `http://<phone-ip>:8080/video` for direct feed

4. **Check firewall**
   ```bash
   # Temporarily disable firewall to test
   sudo ufw disable  # Linux
   ```

5. **Try different URL formats**
   ```bash
   http://192.168.1.100:8080/video
   http://192.168.1.100:8080/videofeed
   http://192.168.1.100:8080/video.mjpeg
   ```

### Poor Performance / Low FPS

**Problem:** FPS < 10, high latency

**Solutions:**

1. **Lower phone resolution**
   - In IP Webcam app: Video resolution → 640x480

2. **Reduce quality**
   - In IP Webcam app: Video quality → 50%

3. **Check WiFi signal**
   - Move phone/computer closer to router
   - Use 5GHz WiFi if available

4. **Reduce detection parameters**
   - Increase `min_area` to filter small objects
   - Process every other frame (modify code)

5. **Close other apps**
   - On phone: Close background apps
   - On computer: Close heavy applications

### Stream Keeps Dropping

**Problem:** Connection lost, frequent reconnects

**Solutions:**

1. **Keep phone plugged in**
   - Streaming uses lots of power
   - Phone may throttle when battery low

2. **Disable phone sleep**
   - IP Webcam: Settings → Prevent phone from sleeping

3. **Keep phone screen on**
   - Some apps stop streaming when screen off
   - Use "Stay awake" in Developer options

4. **Check WiFi stability**
   - Run ping test: `ping <phone-ip>`
   - Should have consistent < 50ms response

### Camera Orientation Wrong

**Problem:** Video is sideways or upside down

**Solutions:**

1. **In IP Webcam app**
   - Video Preferences → Video orientation
   - Choose: Landscape or Portrait

2. **Lock phone rotation**
   - Swipe down notification panel
   - Enable "Auto-rotate" lock

### No Weeds Detected

**Problem:** Video shows but no detection boxes

**Solutions:**

1. **Check detection parameters**
   - Use `video_tuner_v2.py` on test video first
   - Adjust HSV ranges and min_area
   - Save settings with 'P' key

2. **Verify lighting**
   - Need good lighting for color detection
   - Avoid harsh shadows

3. **Check camera view**
   - Point at actual green plants
   - Get close enough (2-3 feet)

---

## Performance Optimization

### Optimal Settings

**Phone (IP Webcam):**
- Resolution: 1280x720 (720p)
- Quality: 60-70%
- FPS: 30
- Video encoder: MJPEG (better compatibility)

**Network:**
- Use 5GHz WiFi if possible
- Keep phone < 20 feet from router
- Minimize interference (microwaves, etc.)

**Detection:**
- Use tuned parameters from test videos
- Increase min_area to filter noise (200-400)
- Target 15+ FPS for smooth detection

### Expected Performance

| Resolution | Network  | Expected FPS | Quality   |
|------------|----------|--------------|-----------|
| 640x480    | WiFi 5G  | 25-30        | Low       |
| 1280x720   | WiFi 5G  | 15-25        | Good      |
| 1920x1080  | WiFi 5G  | 10-15        | Best      |
| 1280x720   | WiFi 2.4 | 10-15        | Good      |

---

## Network Discovery Details

### Quick Scan

Scans first 50 IPs on subnet, ports 8080 and 8081 only.

**Speed:** 10-30 seconds
**Accuracy:** ~80% (catches most common setups)

```bash
python3 live_stream_detector.py --quick
```

### Full Scan

Scans entire /24 subnet (254 IPs), multiple ports (8080, 8081, 4747, 8888, 554).

**Speed:** 1-2 minutes
**Accuracy:** ~95% (very thorough)

```bash
python3 live_stream_detector.py --discover
```

### Tested Endpoints

The scanner checks these common paths:
- `/video`
- `/videofeed`
- `/video.mjpeg`
- `/cam`
- `/stream`
- `/mjpeg`

---

## Advanced Usage

### Testing Stream Manager

Test connection without running full detection:

```bash
python3 stream_manager.py http://192.168.1.100:8080/video
```

### Network Discovery CLI

Standalone network scanning:

```bash
# Interactive menu
python3 network_discovery.py

# Quick scan
python3 network_discovery.py --quick

# Manual entry
python3 network_discovery.py --manual
```

### Custom Detection Parameters

Edit detection settings programmatically:

```python
from live_stream_detector import LiveStreamDetector

detector = LiveStreamDetector("http://192.168.1.100:8080/video")

# Adjust parameters
detector.lower_green = np.array([40, 60, 30])
detector.upper_green = np.array([75, 255, 255])
detector.min_area = 300

detector.run()
```

---

## Recommended Android Apps

### IP Webcam (Best for this project)
- **Pros:** Reliable, many options, MJPEG support
- **Cons:** Ads in free version
- **URL format:** `http://<ip>:8080/video`

### DroidCam
- **Pros:** Also works as USB webcam
- **Cons:** Requires client software
- **URL format:** `http://<ip>:4747/video`

### IP Camera Lite
- **Pros:** Simple, lightweight
- **Cons:** Fewer configuration options
- **URL format:** `http://<ip>:8080/video`

---

## Next Steps

1. **Test with phone first**
   - Get live streaming working
   - Verify FPS is acceptable (>15)

2. **Tune detection parameters**
   - Record test video on phone
   - Use `video_tuner_v2.py` to optimize
   - Save settings

3. **Test real-time detection**
   - Point phone at garden/weeds
   - Monitor detection accuracy
   - Adjust parameters if needed

4. **Plan physical setup**
   - Consider phone mounting (tripod, gimbal)
   - Cable management for power
   - Optimal camera height (2-3 feet)

---

## Support

**Common URLs to try:**
```
http://192.168.1.100:8080/video
http://192.168.1.100:8080/videofeed
http://192.168.0.100:8080/video
http://10.0.0.100:8080/video
```

**Still having issues?**
- Check both devices on same WiFi
- Verify phone firewall settings
- Try different IP camera app
- Test with browser first
