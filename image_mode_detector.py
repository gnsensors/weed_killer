#!/usr/bin/env python3
"""
Weed detection on static images
Use this to test with photos before setting up camera
"""

import cv2
import numpy as np
import sys
import os
from datetime import datetime

class WeedDetector:
    def __init__(self):
        self.lower_green = np.array([35, 40, 40])
        self.upper_green = np.array([85, 255, 255])
        self.min_area = 100
        self.max_area = 50000
        os.makedirs("detections", exist_ok=True)
    
    def detect_weeds(self, frame):
        """Detect green objects in frame"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_green, self.upper_green)
        
        kernel = np.ones((5,5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detections = []
        annotated = frame.copy()
        
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            
            if area < self.min_area or area > self.max_area:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
            else:
                cx, cy = x + w//2, y + h//2
            
            perimeter = cv2.arcLength(contour, True)
            circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
            
            detection = {
                'id': i,
                'centroid': (cx, cy),
                'bbox': (x, y, w, h),
                'area': area,
                'circularity': circularity
            }
            detections.append(detection)
            
            cv2.rectangle(annotated, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.circle(annotated, (cx, cy), 5, (0, 0, 255), -1)
            label = f"W{i}: {int(area)}px"
            cv2.putText(annotated, label, (x, y-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return annotated, mask, detections
    
    def process_image(self, image_path):
        """Process a single image file"""
        print(f"\nProcessing: {image_path}")
        
        frame = cv2.imread(image_path)
        if frame is None:
            print(f"ERROR: Could not load image")
            return
        
        print(f"Image size: {frame.shape[1]}x{frame.shape[0]}")
        
        annotated, mask, detections = self.detect_weeds(frame)
        
        print(f"Detected {len(detections)} potential weeds:")
        for det in detections:
            print(f"  Weed {det['id']}: center={det['centroid']}, "
                  f"area={det['area']:.0f}px, circularity={det['circularity']:.2f}")
        
        # Save results
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        cv2.imwrite(f"detections/{base_name}_mask_{timestamp}.jpg", mask)
        cv2.imwrite(f"detections/{base_name}_result_{timestamp}.jpg", annotated)
        print(f"Results saved to detections/")
        
        # Display results
        # Create side-by-side comparison
        h, w = frame.shape[:2]
        mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        
        # Resize if image is too large
        max_width = 1200
        if w > max_width:
            scale = max_width / w
            new_w = int(w * scale)
            new_h = int(h * scale)
            frame = cv2.resize(frame, (new_w, new_h))
            mask_bgr = cv2.resize(mask_bgr, (new_w, new_h))
            annotated = cv2.resize(annotated, (new_w, new_h))
        
        comparison = np.hstack([frame, mask_bgr, annotated])
        
        # Add labels
        cv2.putText(comparison, "Original", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(comparison, "Green Mask", (w + 10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(comparison, f"Detections: {len(detections)}", (2*w + 10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        cv2.imshow('Weed Detection Results (press any key)', comparison)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    def process_directory(self, directory_path):
        """Process all images in a directory"""
        supported_formats = ('.jpg', '.jpeg', '.png', '.bmp')
        
        image_files = [f for f in os.listdir(directory_path) 
                      if f.lower().endswith(supported_formats)]
        
        if not image_files:
            print(f"No image files found in {directory_path}")
            return
        
        print(f"\nFound {len(image_files)} images to process")
        
        for img_file in sorted(image_files):
            img_path = os.path.join(directory_path, img_file)
            self.process_image(img_path)
            print("\nPress any key for next image, 'q' to quit...")
            key = cv2.waitKey(0) & 0xFF
            cv2.destroyAllWindows()
            if key == ord('q'):
                break

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 image_detector.py <image_file>")
        print("  python3 image_detector.py <directory>")
        print("\nExample:")
        print("  python3 image_detector.py test_weed.jpg")
        print("  python3 image_detector.py ./test_images/")
        return
    
    detector = WeedDetector()
    path = sys.argv[1]
    
    if os.path.isfile(path):
        detector.process_image(path)
    elif os.path.isdir(path):
        detector.process_directory(path)
    else:
        print(f"ERROR: {path} is not a valid file or directory")

if __name__ == "__main__":
    main()
