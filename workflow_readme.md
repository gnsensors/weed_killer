# Video-Based Weed Detection Workflow

## Project Overview

This project uses computer vision to detect weeds (green plants) in mulched areas around trees. The workflow allows you to test detection algorithms using phone videos before building the physical robot.

## Directory Structure

```
weed-robot/
├── WORKFLOW.md                    # This file
├── camera_test.py                 # Test camera connectivity
├── weed_detector.py              # Live camera detection
├── image_detector.py             # Process static images
├── video_detector.py             # Process MP4 videos
├── video_tuner.py                # Interactive parameter tuning
├── web_detector.py               # Web-based interface
├── weed_detector_config.json     # Saved detection parameters
├── test_videos/                  # Your recorded videos
├── test_images/                  # Test photos
├── detections/                   # Output from image processing
└── video_detections/             # Output from video processing
    ├── annotated_*.mp4           # Videos with detection overlays
    ├── timeline_*.json           # Frame-by-frame data
    ├── timeline_summary.csv      # Spreadsheet data
    └── keyframes/                # Extracted preview frames
```

## Installation

### On Chromebook (Linux Container)

```bash
# Enable Linux if not already done
# Settings → Advanced → Developers → Linux development environment

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-opencv v4l-utils

# Install Python packages
pip3 install opencv-python numpy flask

# Enable camera access for Linux
# Settings → Linux → Manage USB devices → Enable webcam

# Verify camera
ls -l /dev/video*
v4l2-ctl --list-devices
```

### On Raspberry Pi

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install packages
sudo apt install -y python3-pip python3-opencv python3-picamera2

# Install Python packages
pip3 install opencv-python numpy flask
```

### On Regular Linux/Mac

```bash
pip3 install opencv-python numpy flask
```

---

## Phase 1: Camera Testing

### Test Camera Connectivity

```bash
# Interactive test (requires display)
python3 camera_test.py

# Headless mode (SSH without display)
python3 camera_test.py --headless

# Pi Camera Module
python3 camera_test.py --picam
```

**Expected output:**
- Camera feed displayed or images saved
- No errors about missing camera

---

## Phase 2: Static Image Testing

### Quick Test with Photos

1. **Capture test images** with your phone of mulched areas with weeds
2. **Transfer to Chromebook** via Google Drive, USB, etc.
3. **Place in test_images/** folder

```bash
# Create test directory
mkdir -p test_images

# Process single image
python3 image_detector.py test_images/weed1.jpg

# Process entire directory
python3 image_detector.py test_images/
```

**What to look for:**
- Green plants correctly highlighted
- False positives (mulch detected as weeds)
- Missed weeds

---

## Phase 3: Video Recording

### Recording Guidelines

**Phone settings:**
- 1080p resolution (1920x1080)
- 30 FPS
- Hold steady or use gimbal/stabilizer
- Good lighting (morning, cloudy, or late afternoon)

**Recording technique:**
1. Hold phone 2-3 feet above ground (future robot camera height)
2. Point camera straight down or at slight angle
3. Walk slowly (1-2 ft/second)
4. Pan smoothly across mulched areas
5. Include variety: different weed sizes, lighting conditions
6. Keep videos short: 30-60 seconds each

**Test scenarios to record:**
- `morning_walk.mp4` - Early morning lighting
- `noon_walk.mp4` - Harsh midday sun
- `cloudy_walk.mp4` - Overcast conditions
- `slow_walk.mp4` - Very slow pan
- `fast_walk.mp4` - Normal walking speed
- `height_test_1ft.mp4` - Camera 1 foot high
- `height_test_2ft.mp4` - Camera 2 feet high
- `height_test_3ft.mp4` - Camera 3 feet high

### Transfer Videos

```bash
# Create videos directory
mkdir -p test_videos

# Transfer from phone via:
# - USB cable and file browser
# - Google Drive/Photos
# - ADB: adb pull /sdcard/DCIM/Camera/video.mp4 test_videos/
```

---

## Phase 4: Interactive Parameter Tuning

### Find Optimal Detection Settings

```bash
# Open video in tuning mode
python3 video_tuner.py test_videos/morning_walk.mp4
```

**Interface controls:**
- **Trackbars:** Adjust HSV ranges and minimum area
- **SPACE:** Play/pause video
- **RIGHT/LEFT arrows:** Next/previous frame
- **UP/DOWN arrows:** Skip forward/backward 10 frames
- **'r' key:** Reset to default parameters
- **'s' key:** Save current settings to `weed_detector_config.json`
- **'q' key:** Quit

**Display panels:**
1. **Left:** Original video frame
2. **Middle:** Green mask (white = detected green)
3. **Right:** Detection results with bounding boxes

### Tuning Strategy

1. **Find a representative frame** with typical weeds
2. **Adjust Hue (H):**
   - Low: 35 (yellowish-green)
   - High: 85 (bluish-green)
   - Narrow range if detecting non-green objects
3. **Adjust Saturation (S):**
   - Low: Start at 40, increase to 60-80 if brown mulch is detected
   - High: Keep at 255
   - Higher S Low = more vibrant colors only
4. **Adjust Value (V):**
   - Low: Decrease if missing weeds in shadows (try 20-30)
   - High: Keep at 255
   - Controls brightness range
5. **Adjust Min Area:**
   - Increase to filter small debris/noise
   - Decrease to catch smaller weeds
   - Typical range: 100-300 pixels

**Validation:**
- Scrub through entire video
- Check multiple lighting conditions
- Verify consistent detection
- Minimize false positives

**Save when satisfied:**
- Press 's' to save to `weed_detector_config.json`
- These settings will be used by batch processing

---

## Phase 5: Batch Video Processing

### Process Entire Videos

```bash
# Basic processing (uses saved config)
python3 video_detector.py test_videos/morning_walk.mp4

# Watch processing in real-time
python3 video_detector.py test_videos/morning_walk.mp4 --interactive

# Faster processing for long videos (process every 5th frame)
python3 video_detector.py test_videos/long_video.mp4 --sample 5

# Extract more keyframes for preview
python3 video_detector.py test_videos/test.mp4 --keyframes 20

# Combine options
python3 video_detector.py test_videos/test.mp4 --interactive --sample 3
```

### Understanding Output

**Console statistics:**
```
=== Analysis ===
Total frames analyzed: 900
Average weeds per frame: 4.2
Max weeds in frame: 12
Min weeds in frame: 0

Top 5 frames with most weeds:
  1. Frame 450 at 0:00:15: 12 weeds
  2. Frame 523 at 0:00:17: 11 weeds

Weed size statistics:
  Average area: 850 pixels
  Largest weed: 2340 pixels
  Smallest weed: 120 pixels

Detection coverage: 85.3% of frames have weeds
```

**Output files:**
- `video_detections/annotated_*.mp4` - Video with green boxes and labels
- `video_detections/timeline_*.json` - Detailed frame-by-frame data
- `video_detections/timeline_summary.csv` - Easy spreadsheet analysis
- `video_detections/keyframes/*.jpg` - Preview images

### Annotated Video Features

- **Green boxes:** Weed boundaries
- **Red dots:** Weed centers (brush target points)
- **Labels:** Weed ID and size in pixels
- **Overlay info:**
  - Current timestamp
  - Frame number
  - Weed count
  - Progress bar

---

## Phase 6: Analysis

### Review Annotated Video

Open `video_detections/annotated_*.mp4` and check:
- ✓ Weeds correctly identified
- ✗ False positives (mulch, sticks, debris)
- ✗ False negatives (missed weeds)
- Detection consistency across frames

### Analyze CSV Data

Open `video_detections/timeline_summary.csv` in Google Sheets or Excel:

**Create graphs:**
1. **Weed Count vs Time:** Shows detection density
2. **Average Area vs Time:** Shows weed size variation
3. **Max Area per Frame:** Identifies largest weeds

**Key metrics:**
- Detection coverage: % of frames with weeds (target: >80%)
- Average weeds per frame: Density measure
- Area consistency: Large variance may indicate false positives

### Review JSON Data

```bash
# Pretty print timeline
python3 -m json.tool video_detections/timeline_morning_walk.json | less

# Extract specific data with jq (if installed)
cat video_detections/timeline_*.json | jq '.[] | select(.weed_count > 5)'
```

**JSON structure:**
```json
{
  "frame": 150,
  "timestamp": "0:00:05",
  "timestamp_sec": 5.0,
  "weed_count": 3,
  "detections": [
    {
      "id": 0,
      "centroid": [320, 240],
      "bbox": [300, 220, 40, 40],
      "area": 1580,
      "circularity": 0.85,
      "aspect_ratio": 1.0
    }
  ]
}
```

---

## Phase 7: Optimization

### Test Matrix

Create a test matrix to find optimal conditions:

| Video File | Lighting | Speed | Height | Coverage | Avg Weeds | Notes |
|------------|----------|-------|--------|----------|-----------|-------|
| test1.mp4 | Morning | Slow | 2ft | 87% | 4.2 | Best results |
| test2.mp4 | Noon | Slow | 2ft | 65% | 3.1 | Shadows problematic |
| test3.mp4 | Cloudy | Fast | 2ft | 72% | 3.8 | Motion blur |

### Common Issues and Solutions

**Low detection coverage (<60%)**
- [ ] Lower S Low threshold (detect paler greens)
- [ ] Reduce Min Area (catch smaller weeds)
- [ ] Improve lighting (avoid harsh shadows)
- [ ] Slow down camera movement

**Too many false positives**
- [ ] Increase S Low (60-80 range)
- [ ] Increase Min Area (200-400)
- [ ] Narrow H range (40-75 instead of 35-85)
- [ ] Use different mulch background

**Inconsistent detection**
- [ ] Stabilize camera (use gimbal)
- [ ] Walk slower
- [ ] Record at consistent height
- [ ] Process more frequently (lower --sample rate)

**Missing weeds in shadows**
- [ ] Decrease V Low (try 20-30)
- [ ] Record during diffuse lighting (cloudy)
- [ ] Avoid midday sun

### Document Optimal Configuration

After testing, document your findings:

```markdown
## Optimal Configuration

### Camera Setup
- Height: 24 inches above ground
- Angle: Straight down (90°)
- Frame rate: 30 FPS
- Resolution: 1080p

### Operating Conditions
- Lighting: Morning (7-10am) or cloudy
- Travel speed: <0.5 mph (~8 inches/second)
- Avoid: Midday sun (harsh shadows)

### Detection Parameters
- H Low: 40
- H High: 75
- S Low: 65
- S High: 255
- V Low: 30
- V High: 255
- Min Area: 180 pixels

### Performance Metrics
- Detection coverage: 85%
- Average weeds per frame: 4.5
- False positive rate: <10%
- Processing speed: 15 FPS on Raspberry Pi 4
```

---

## Phase 8: Web Interface (Optional)

For easier testing without OpenCV windows:

```bash
# Start web server
python3 web_detector.py

# Open browser
# http://localhost:5000
# or from another device: http://<chromebook-ip>:5000
```

**Features:**
- Live camera feed with detections
- Real-time parameter adjustment with sliders
- Save/load configurations
- View detection statistics
- No need for OpenCV display windows

---

## Next Steps: Hardware Integration

Once you have solid detection working on video:

### 1. Transfer to Raspberry Pi

```bash
# From Chromebook to Pi
scp *.py weed_detector_config.json pi@raspberrypi.local:~/weed-robot/

# Or use Git
git init
git add *.py *.json *.md
git commit -m "Working weed detection"
git push origin main

# On Pi
git clone <your-repo>
```

### 2. Test with Pi Camera

```bash
# On Raspberry Pi
python3 camera_test.py

# Run live detection
python3 weed_detector.py
```

### 3. Plan Hardware Build

Based on your video analysis, you now know:
- Required camera specifications
- Optimal mounting height and angle
- Processing speed requirements
- Operating speed limits
- Best lighting conditions

**Phase 2 Hardware** (from original plan):
- Mobile chassis (4WD rover or tracked)
- Raspberry Pi 4 (4GB)
- Pi Camera or USB webcam
- 12V battery system
- Motor controllers
- Weed elimination mechanism (brush, blade, or thermal)

### 4. Integration Path

```
Video Testing (Current) 
  → Live Camera on Stationary Mount
  → Camera on Remote-Controlled Platform
  → Add GPS/Positioning
  → Add Weed Elimination Mechanism
  → Full Autonomous Operation
```

---

## Tips and Best Practices

### Recording Videos

**DO:**
- Record multiple short clips vs one long video
- Include variety in lighting, speed, height
- Label files descriptively (e.g., `morning_2ft_slow.mp4`)
- Keep camera steady
- Record same area at different times of day

**DON'T:**
- Record in 4K (harder to process, unnecessary)
- Walk too fast (motion blur)
- Record only in perfect conditions
- Forget to test edge cases (shadows, wet mulch, etc.)

### Processing Videos

**Quick iteration:**
```bash
# Extract keyframes only (fast)
python3 video_detector.py test.mp4 --keyframes 20

# Review keyframes in video_detections/keyframes/

# If promising, process full video
python3 video_detector.py test.mp4
```

**Long videos:**
```bash
# Sample every 5th frame (5x faster)
python3 video_detector.py long.mp4 --sample 5

# Sample every 10th frame (10x faster, lower accuracy)
python3 video_detector.py long.mp4 --sample 10
```

### Parameter Tuning

**Start broad, then narrow:**
1. Use default H range [35-85] initially
2. If detecting brown objects, increase S Low
3. If missing weeds, decrease S Low and V Low
4. Fine-tune in 5-point increments
5. Test on multiple videos before finalizing

**Save multiple configs:**
```bash
# Save variations
cp weed_detector_config.json configs/morning_config.json
cp weed_detector_config.json configs/cloudy_config.json

# Test which works best
# May need different configs for different conditions
```

---

## Troubleshooting

### Camera not detected

```bash
# Check device
ls -l /dev/video*

# Check permissions
sudo usermod -a -G video $USER
# Logout and login

# Try different index
# Edit scripts: camera_index = 1 (instead of 0)
```

### OpenCV display not working

```bash
# Use headless mode
python3 camera_test.py --headless

# Or use web interface
python3 web_detector.py

# Or SSH with X11 forwarding
ssh -X pi@raspberrypi.local
```

### Poor detection results

1. Review video quality (stable? clear? good lighting?)
2. Use video_tuner.py to find better parameters
3. Try processing keyframes only to iterate faster
4. Check that weed_detector_config.json is being loaded
5. Verify green objects are actually in frame

### Video processing too slow

```bash
# Increase sample rate
python3 video_detector.py video.mp4 --sample 10

# Or process on more powerful computer first
# Then transfer results

# Or just extract keyframes
python3 video_detector.py video.mp4 --keyframes 30
```

---

## References

### HSV Color Space

- **H (Hue):** 0-179 in OpenCV
  - Red: 0-10, 170-179
  - Yellow: 20-30
  - Green: 35-85
  - Blue: 90-130
- **S (Saturation):** 0-255
  - 0: Grayscale
  - 255: Pure color
- **V (Value):** 0-255
  - 0: Black
  - 255: Bright

### Typical Green Plant Ranges

- **Vibrant grass:** H[35-75], S[80-255], V[80-255]
- **Pale weeds:** H[35-85], S[40-150], V[40-255]
- **Dark green:** H[40-80], S[60-255], V[30-180]
- **In shadows:** Decrease V Low to 20-30

### Performance Targets

- **Detection coverage:** >80% of frames
- **False positive rate:** <15%
- **Processing speed:** >10 FPS for real-time use
- **Detection latency:** <100ms per frame

---

## Contact and Collaboration

When working with Claude in VS Code:

1. **Ask for code modifications:** "Update video_detector.py to add feature X"
2. **Request new features:** "Create a script to compare two config files"
3. **Debug issues:** Share error messages and ask for fixes
4. **Optimize performance:** "How can I speed up video processing?"
5. **Add functionality:** "Add export to different video formats"

---

## Version History

- **v1.0:** Initial workflow with video detection
- Camera testing, image processing, video analysis
- Interactive tuning interface
- Web-based interface option

---

## License

This project is for educational and personal use. Modify and adapt as needed for your specific weed detection application.