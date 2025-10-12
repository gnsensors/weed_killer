#!/usr/bin/env python3
"""
Simple camera test script for Raspberry Pi
Tests both USB webcam and Pi Camera Module
"""

import cv2
import sys
from datetime import datetime

def test_usb_camera(camera_index=0):
    """Test USB webcam"""
    print(f"Testing USB camera at index {camera_index}...")
    
    cap = cv2.VideoCapture(camera_index)
    
    if not cap.isOpened():
        print(f"ERROR: Could not open camera {camera_index}")
        return False
    
    # Set resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print("Camera opened successfully!")
    print(f"Resolution: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
    print("\nPress 's' to save image, 'q' to quit")
    
    frame_count = 0
    while True:
        ret, frame = cap.read()
        
        if not ret:
            print("ERROR: Failed to grab frame")
            break
        
        frame_count += 1
        
        # Add info overlay
        cv2.putText(frame, f"Frame: {frame_count}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, "Press 's' to save, 'q' to quit", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Display (only works if you have display attached or X11 forwarding)
        cv2.imshow('Camera Test', frame)
        
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            print("\nQuitting...")
            break
        elif key == ord('s'):
            filename = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            cv2.imwrite(filename, frame)
            print(f"Saved: {filename}")
    
    cap.release()
    cv2.destroyAllWindows()
    return True

def test_pi_camera():
    """Test Pi Camera Module using picamera2"""
    try:
        from picamera2 import Picamera2
    except ImportError:
        print("ERROR: picamera2 not installed")
        print("Install with: sudo apt install -y python3-picamera2")
        return False
    
    print("Testing Pi Camera Module...")
    
    picam = Picamera2()
    config = picam.create_still_configuration(main={"size": (640, 480)})
    picam.configure(config)
    picam.start()
    
    print("Camera started successfully!")
    print("Taking test photo...")
    
    import time
    time.sleep(2)  # Let camera adjust
    
    filename = f"picam_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    picam.capture_file(filename)
    print(f"Saved: {filename}")
    
    picam.stop()
    return True

def capture_headless(camera_index=0, num_images=5, interval=2):
    """Capture images without display (for SSH sessions)"""
    print(f"Headless capture mode: {num_images} images, {interval}s interval")
    
    cap = cv2.VideoCapture(camera_index)
    
    if not cap.isOpened():
        print(f"ERROR: Could not open camera {camera_index}")
        return False
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    import time
    
    for i in range(num_images):
        ret, frame = cap.read()
        
        if not ret:
            print(f"ERROR: Failed to capture frame {i+1}")
            continue
        
        filename = f"capture_{i+1:03d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        cv2.imwrite(filename, frame)
        print(f"Captured: {filename}")
        
        if i < num_images - 1:
            time.sleep(interval)
    
    cap.release()
    print("Done!")
    return True

if __name__ == "__main__":
    print("=== Raspberry Pi Camera Test ===\n")
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--headless":
            # Headless mode for SSH sessions
            capture_headless(camera_index=0, num_images=5, interval=2)
        elif sys.argv[1] == "--picam":
            # Test Pi Camera Module
            test_pi_camera()
        else:
            print("Usage:")
            print("  python3 camera_test.py              # Interactive USB camera test")
            print("  python3 camera_test.py --headless   # Capture images without display")
            print("  python3 camera_test.py --picam      # Test Pi Camera Module")
    else:
        # Interactive USB camera test
        test_usb_camera(camera_index=0)
