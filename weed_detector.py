#!/usr/bin/env python3
"""
Simple green weed detection using color thresholding
Identifies green objects (potential weeds) in mulch areas
"""

import cv2
import numpy as np
from datetime import datetime
import json
import os

class WeedDetector:
    def __init__(self):
        # HSV color range for green plants
        # These are starting values - tune based on your lighting/weeds
        self.lower_green = np.array([35, 40, 40])    # Lower bound of green in HSV
        self.upper_green = np.array([85, 255, 255])  # Upper bound of green in HSV
        
        # Detection parameters
        self.min_area = 100      # Minimum contour area (pixels) to consider
        self.max_area = 50000    # Maximum area (filters out very large objects)
        
        # Create output directory
        os.makedirs("detections", exist_ok=True)
    
    def detect_weeds(self, frame):
        """
        Detect green objects (potential weeds) in frame
        Returns: annotated frame, list of weed contours, detection data
        """
        # Convert to HSV color space (better for color detection)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Create mask for green colors
        mask = cv2.inRange(hsv, self.lower_green, self.upper_green)
        
        # Clean up mask with morphological operations
        kernel = np.ones((5,5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)   # Remove noise
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)  # Fill gaps
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter and analyze contours
        detections = []
        annotated = frame.copy()
        
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            
            # Filter by area
            if area < self.min_area or area > self.max_area:
                continue
            
            # Get bounding box and centroid
            x, y, w, h = cv2.boundingRect(contour)
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
            else:
                cx, cy = x + w//2, y + h//2
            
            # Calculate additional features
            perimeter = cv2.arcLength(contour, True)
            circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
            aspect_ratio = float(w) / h if h > 0 else 0
            
            # Store detection data
            detection = {
                'id': i,
                'centroid': (cx, cy),
                'bbox': (x, y, w, h),
                'area': area,
                'circularity': circularity,
                'aspect_ratio': aspect_ratio
            }
            detections.append(detection)
            
            # Draw on annotated image
            # Bounding box
            cv2.rectangle(annotated, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # Centroid
            cv2.circle(annotated, (cx, cy), 5, (0, 0, 255), -1)
            
            # Label
            label = f"W{i}: {int(area)}px"
            cv2.putText(annotated, label, (x, y-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return annotated, mask, detections
    
    def tune_parameters(self, frame):
        """
        Interactive tuning mode with trackbars
        Use this to adjust HSV thresholds for your specific conditions
        """
        window_name = "Tuning Mode"
        cv2.namedWindow(window_name)
        
        # Create trackbars for HSV ranges
        cv2.createTrackbar('H Low', window_name, self.lower_green[0], 179, lambda x: None)
        cv2.createTrackbar('H High', window_name, self.upper_green[0], 179, lambda x: None)
        cv2.createTrackbar('S Low', window_name, self.lower_green[1], 255, lambda x: None)
        cv2.createTrackbar('S High', window_name, self.upper_green[1], 255, lambda x: None)
        cv2.createTrackbar('V Low', window_name, self.lower_green[2], 255, lambda x: None)
        cv2.createTrackbar('V High', window_name, self.upper_green[2], 255, lambda x: None)
        cv2.createTrackbar('Min Area', window_name, self.min_area, 1000, lambda x: None)
        
        print("\nTuning Mode:")
        print("- Adjust trackbars to isolate weeds")
        print("- Press 's' to save current settings")
        print("- Press 'q' to quit")
        
        while True:
            # Get current trackbar positions
            h_low = cv2.getTrackbarPos('H Low', window_name)
            h_high = cv2.getTrackbarPos('H High', window_name)
            s_low = cv2.getTrackbarPos('S Low', window_name)
            s_high = cv2.getTrackbarPos('S High', window_name)
            v_low = cv2.getTrackbarPos('V Low', window_name)
            v_high = cv2.getTrackbarPos('V High', window_name)
            min_area = cv2.getTrackbarPos('Min Area', window_name)
            
            # Update detector parameters
            self.lower_green = np.array([h_low, s_low, v_low])
            self.upper_green = np.array([h_high, s_high, v_high])
            self.min_area = min_area
            
            # Run detection
            annotated, mask, detections = self.detect_weeds(frame)
            
            # Create display
            mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            display = np.hstack([frame, mask_bgr, annotated])
            
            # Add info text
            info_text = f"Detections: {len(detections)}"
            cv2.putText(display, info_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            cv2.imshow(window_name, display)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                self.save_settings()
                print("Settings saved!")
        
        cv2.destroyAllWindows()
    
    def save_settings(self, filename="weed_detector_config.json"):
        """Save current detection parameters"""
        config = {
            'lower_green': self.lower_green.tolist(),
            'upper_green': self.upper_green.tolist(),
            'min_area': self.min_area,
            'max_area': self.max_area
        }
        with open(filename, 'w') as f:
            json.dump(config, f, indent=4)
        print(f"Configuration saved to {filename}")
    
    def load_settings(self, filename="weed_detector_config.json"):
        """Load detection parameters"""
        try:
            with open(filename, 'r') as f:
                config = json.load(f)
            self.lower_green = np.array(config['lower_green'])
            self.upper_green = np.array(config['upper_green'])
            self.min_area = config['min_area']
            self.max_area = config['max_area']
            print(f"Configuration loaded from {filename}")
        except FileNotFoundError:
            print(f"Config file not found, using defaults")

def main():
    import sys
    
    # Initialize detector
    detector = WeedDetector()
    
    # Try to load previous settings
    detector.load_settings()
    
    # Setup camera
    camera_index = 0
    cap = cv2.VideoCapture(camera_index)
    
    if not cap.isOpened():
        print("ERROR: Could not open camera")
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print("\n=== Weed Detection System ===")
    print("Commands:")
    print("  SPACE - Capture and analyze current frame")
    print("  't'   - Enter tuning mode")
    print("  's'   - Save detection results")
    print("  'q'   - Quit")
    print("\nStarting live preview...\n")
    
    frame_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame")
                break
            
            frame_count += 1
            
            # Run detection on every frame (for live preview)
            annotated, mask, detections = detector.detect_weeds(frame)
            
            # Add frame info
            cv2.putText(annotated, f"Weeds: {len(detections)}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(annotated, "SPACE=capture, t=tune, s=save, q=quit", (10, 460),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            
            cv2.imshow('Weed Detection', annotated)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord(' '):
                # Capture and save detailed analysis
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                
                cv2.imwrite(f"detections/original_{timestamp}.jpg", frame)
                cv2.imwrite(f"detections/mask_{timestamp}.jpg", mask)
                cv2.imwrite(f"detections/annotated_{timestamp}.jpg", annotated)
                
                # Save detection data
                with open(f"detections/data_{timestamp}.json", 'w') as f:
                    json.dump(detections, f, indent=4)
                
                print(f"Captured frame {frame_count}: {len(detections)} weeds detected")
                for det in detections:
                    print(f"  Weed {det['id']}: center={det['centroid']}, area={det['area']:.0f}px")
            
            elif key == ord('t'):
                # Enter tuning mode with current frame
                detector.tune_parameters(frame)
            
            elif key == ord('s'):
                detector.save_settings()
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("\nShutdown complete")

if __name__ == "__main__":
    main()
