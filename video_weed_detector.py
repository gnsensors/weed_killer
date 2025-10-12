#!/usr/bin/env python3
"""
Video-based weed detection with timeline tracking
Process MP4 videos and track weed positions over time
"""

import cv2
import numpy as np
import json
import os
from datetime import datetime, timedelta
import sys

class VideoWeedDetector:
    def __init__(self):
        # HSV color range for green plants
        self.lower_green = np.array([35, 40, 40])
        self.upper_green = np.array([85, 255, 255])
        self.min_area = 100
        self.max_area = 50000
        
        # Video tracking
        self.timeline_data = []
        
        # Create output directory
        self.output_dir = "video_detections"
        os.makedirs(self.output_dir, exist_ok=True)
    
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
            aspect_ratio = float(w) / h if h > 0 else 0
            
            detection = {
                'id': i,
                'centroid': (cx, cy),
                'bbox': (x, y, w, h),
                'area': int(area),
                'circularity': round(circularity, 3),
                'aspect_ratio': round(aspect_ratio, 3)
            }
            detections.append(detection)
            
            # Draw on annotated image
            cv2.rectangle(annotated, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.circle(annotated, (cx, cy), 5, (0, 0, 255), -1)
            
            # Label with more info
            label = f"W{i}: {int(area)}px"
            cv2.putText(annotated, label, (x, y-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return annotated, mask, detections
    
    def process_video(self, video_path, sample_rate=1, interactive=False):
        """
        Process video file and track detections over time
        
        Args:
            video_path: Path to MP4 video file
            sample_rate: Process every Nth frame (1=all frames, 5=every 5th frame)
            interactive: Show video while processing if True
        """
        print(f"\nProcessing video: {video_path}")
        
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            print("ERROR: Could not open video file")
            return
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration_sec = total_frames / fps if fps > 0 else 0
        
        print(f"Video info:")
        print(f"  Resolution: {width}x{height}")
        print(f"  FPS: {fps:.2f}")
        print(f"  Total frames: {total_frames}")
        print(f"  Duration: {duration_sec:.2f} seconds")
        print(f"  Sample rate: Processing every {sample_rate} frame(s)")
        print(f"\nProcessing...")
        
        # Prepare output video
        output_path = os.path.join(self.output_dir, 
                                   f"annotated_{os.path.basename(video_path)}")
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps/sample_rate, (width, height))
        
        # Reset timeline data
        self.timeline_data = []
        
        frame_count = 0
        processed_count = 0
        
        while True:
            ret, frame = cap.read()
            
            if not ret:
                break
            
            frame_count += 1
            
            # Sample frames based on sample_rate
            if frame_count % sample_rate != 0:
                continue
            
            processed_count += 1
            
            # Calculate timestamp
            timestamp_sec = frame_count / fps if fps > 0 else 0
            timestamp_str = str(timedelta(seconds=int(timestamp_sec)))
            
            # Detect weeds
            annotated, mask, detections = self.detect_weeds(frame)
            
            # Add overlay info
            info_y = 30
            cv2.putText(annotated, f"Time: {timestamp_str}", (10, info_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(annotated, f"Frame: {frame_count}/{total_frames}", (10, info_y + 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(annotated, f"Weeds: {len(detections)}", (10, info_y + 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Progress bar
            progress = frame_count / total_frames
            bar_width = width - 20
            bar_height = 20
            bar_y = height - 30
            cv2.rectangle(annotated, (10, bar_y), (10 + bar_width, bar_y + bar_height),
                         (100, 100, 100), -1)
            cv2.rectangle(annotated, (10, bar_y), 
                         (10 + int(bar_width * progress), bar_y + bar_height),
                         (0, 255, 0), -1)
            
            # Record timeline data
            frame_data = {
                'frame': frame_count,
                'timestamp': timestamp_str,
                'timestamp_sec': round(timestamp_sec, 2),
                'weed_count': len(detections),
                'detections': detections
            }
            self.timeline_data.append(frame_data)
            
            # Write to output video
            out.write(annotated)
            
            # Display if interactive
            if interactive:
                display = cv2.resize(annotated, (960, 540))  # Smaller for display
                cv2.imshow('Video Processing (press q to quit)', display)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\nProcessing interrupted by user")
                    break
            
            # Progress update
            if processed_count % 30 == 0:
                print(f"  Processed {frame_count}/{total_frames} frames "
                      f"({progress*100:.1f}%) - {len(detections)} weeds detected")
        
        cap.release()
        out.release()
        if interactive:
            cv2.destroyAllWindows()
        
        print(f"\nProcessing complete!")
        print(f"  Processed {processed_count} frames")
        print(f"  Output video: {output_path}")
        
        # Save timeline data
        self.save_timeline_data(video_path)
        
        # Generate analysis
        self.analyze_timeline()
    
    def save_timeline_data(self, video_path):
        """Save timeline data to JSON file"""
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        json_path = os.path.join(self.output_dir, f"timeline_{base_name}.json")
        
        with open(json_path, 'w') as f:
            json.dump(self.timeline_data, f, indent=2)
        
        print(f"  Timeline data: {json_path}")
    
    def analyze_timeline(self):
        """Generate analysis and statistics from timeline data"""
        if not self.timeline_data:
            return
        
        print("\n=== Analysis ===")
        
        # Overall statistics
        total_frames = len(self.timeline_data)
        weed_counts = [frame['weed_count'] for frame in self.timeline_data]
        
        avg_weeds = np.mean(weed_counts)
        max_weeds = np.max(weed_counts)
        min_weeds = np.min(weed_counts)
        
        print(f"Total frames analyzed: {total_frames}")
        print(f"Average weeds per frame: {avg_weeds:.1f}")
        print(f"Max weeds in frame: {max_weeds}")
        print(f"Min weeds in frame: {min_weeds}")
        
        # Find frames with most weeds
        frames_by_weeds = sorted(self.timeline_data, 
                                key=lambda x: x['weed_count'], 
                                reverse=True)
        
        print("\nTop 5 frames with most weeds:")
        for i, frame in enumerate(frames_by_weeds[:5]):
            print(f"  {i+1}. Frame {frame['frame']} at {frame['timestamp']}: "
                  f"{frame['weed_count']} weeds")
        
        # Weed size analysis
        all_areas = []
        for frame in self.timeline_data:
            for det in frame['detections']:
                all_areas.append(det['area'])
        
        if all_areas:
            print(f"\nWeed size statistics:")
            print(f"  Average area: {np.mean(all_areas):.0f} pixels")
            print(f"  Largest weed: {np.max(all_areas):.0f} pixels")
            print(f"  Smallest weed: {np.min(all_areas):.0f} pixels")
        
        # Detection consistency
        frames_with_weeds = sum(1 for frame in self.timeline_data if frame['weed_count'] > 0)
        coverage = (frames_with_weeds / total_frames) * 100
        print(f"\nDetection coverage: {coverage:.1f}% of frames have weeds")
        
        # Generate CSV for easy analysis
        self.export_to_csv()
    
    def export_to_csv(self):
        """Export timeline data to CSV for spreadsheet analysis"""
        csv_path = os.path.join(self.output_dir, "timeline_summary.csv")
        
        with open(csv_path, 'w') as f:
            f.write("Frame,Timestamp,Timestamp_Sec,Weed_Count,Avg_Area,Max_Area\n")
            
            for frame in self.timeline_data:
                areas = [det['area'] for det in frame['detections']]
                avg_area = np.mean(areas) if areas else 0
                max_area = np.max(areas) if areas else 0
                
                f.write(f"{frame['frame']},{frame['timestamp']},"
                       f"{frame['timestamp_sec']},{frame['weed_count']},"
                       f"{avg_area:.0f},{max_area}\n")
        
        print(f"  CSV export: {csv_path}")
    
    def extract_keyframes(self, video_path, num_frames=10):
        """Extract evenly-spaced keyframes from video for quick review"""
        print(f"\nExtracting {num_frames} keyframes...")
        
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        keyframe_dir = os.path.join(self.output_dir, "keyframes")
        os.makedirs(keyframe_dir, exist_ok=True)
        
        interval = total_frames // num_frames
        
        for i in range(num_frames):
            frame_num = i * interval
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            
            if ret:
                annotated, mask, detections = self.detect_weeds(frame)
                
                filename = os.path.join(keyframe_dir, 
                                       f"keyframe_{i+1:02d}_frame{frame_num}.jpg")
                cv2.imwrite(filename, annotated)
                print(f"  Saved: {filename} ({len(detections)} weeds)")
        
        cap.release()
        print(f"Keyframes saved to: {keyframe_dir}")
    
    def load_settings(self, filename="weed_detector_config.json"):
        """Load detection parameters"""
        try:
            with open(filename, 'r') as f:
                config = json.load(f)
            self.lower_green = np.array(config['lower_green'])
            self.upper_green = np.array(config['upper_green'])
            self.min_area = config['min_area']
            self.max_area = config['max_area']
            print(f"Loaded configuration from {filename}")
        except FileNotFoundError:
            print("No config file found, using defaults")

def main():
    if len(sys.argv) < 2:
        print("Video Weed Detection System")
        print("\nUsage:")
        print("  python3 video_detector.py <video_file.mp4> [options]")
        print("\nOptions:")
        print("  --interactive     Show video while processing")
        print("  --sample N        Process every Nth frame (default: 1)")
        print("  --keyframes N     Extract N keyframes (default: 10)")
        print("\nExamples:")
        print("  python3 video_detector.py garden.mp4")
        print("  python3 video_detector.py garden.mp4 --interactive")
        print("  python3 video_detector.py garden.mp4 --sample 5")
        print("  python3 video_detector.py garden.mp4 --keyframes 20")
        return
    
    video_path = sys.argv[1]
    
    if not os.path.exists(video_path):
        print(f"ERROR: Video file not found: {video_path}")
        return
    
    # Parse options
    interactive = '--interactive' in sys.argv
    
    sample_rate = 1
    if '--sample' in sys.argv:
        idx = sys.argv.index('--sample')
        if idx + 1 < len(sys.argv):
            sample_rate = int(sys.argv[idx + 1])
    
    num_keyframes = 10
    if '--keyframes' in sys.argv:
        idx = sys.argv.index('--keyframes')
        if idx + 1 < len(sys.argv):
            num_keyframes = int(sys.argv[idx + 1])
    
    # Initialize detector
    detector = VideoWeedDetector()
    detector.load_settings()
    
    print("=== Video Weed Detection System ===\n")
    
    # Extract keyframes first for quick preview
    detector.extract_keyframes(video_path, num_keyframes)
    
    # Process full video
    detector.process_video(video_path, sample_rate=sample_rate, interactive=interactive)
    
    print("\n=== Processing Complete ===")
    print(f"Check the '{detector.output_dir}' folder for:")
    print("  - Annotated video with detection overlays")
    print("  - Timeline JSON with frame-by-frame data")
    print("  - CSV summary for analysis")
    print("  - Keyframe images")

if __name__ == "__main__":
    main()
