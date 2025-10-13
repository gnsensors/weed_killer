#!/usr/bin/env python3
"""
Interactive tuning tool for video weed detection
Use this to find optimal parameters for your videos
"""

import cv2
import numpy as np
import json
import sys

class VideoTuner:
    def __init__(self, video_path):
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        
        if not self.cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
        
        # Detection parameters
        self.lower_green = np.array([35, 40, 40])
        self.upper_green = np.array([85, 255, 255])
        self.min_area = 100
        self.max_area = 50000
        
        # Video properties
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.current_frame = 0
    
    def detect_weeds(self, frame):
        """Run detection on frame"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_green, self.upper_green)
        
        kernel = np.ones((5,5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        annotated = frame.copy()
        weed_count = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            
            if area < self.min_area or area > self.max_area:
                continue
            
            weed_count += 1
            x, y, w, h = cv2.boundingRect(contour)
            
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
            else:
                cx, cy = x + w//2, y + h//2
            
            cv2.rectangle(annotated, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.circle(annotated, (cx, cy), 5, (0, 0, 255), -1)
            cv2.putText(annotated, f"{int(area)}", (x, y-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        
        return annotated, mask, weed_count
    
    def seek_frame(self, frame_number):
        """Jump to specific frame"""
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        self.current_frame = frame_number
    
    def run(self):
        """Run interactive tuning interface"""
        window = "Video Tuner - Use trackbars and keyboard"
        cv2.namedWindow(window, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window, 1600, 900)
        
        # Create trackbars
        cv2.createTrackbar('H Low', window, self.lower_green[0], 179, lambda x: None)
        cv2.createTrackbar('H High', window, self.upper_green[0], 179, lambda x: None)
        cv2.createTrackbar('S Low', window, self.lower_green[1], 255, lambda x: None)
        cv2.createTrackbar('S High', window, self.upper_green[1], 255, lambda x: None)
        cv2.createTrackbar('V Low', window, self.lower_green[2], 255, lambda x: None)
        cv2.createTrackbar('V High', window, self.upper_green[2], 255, lambda x: None)
        cv2.createTrackbar('Min Area', window, self.min_area, 2000, lambda x: None)
        cv2.createTrackbar('Frame', window, 0, self.total_frames-1, lambda x: None)
        
        print("\n=== Video Tuning Mode ===")
        print("Keyboard controls:")
        print("  SPACE  - Play/Pause")
        print("  RIGHT  - Next frame")
        print("  LEFT   - Previous frame")
        print("  UP     - Forward 10 frames")
        print("  DOWN   - Backward 10 frames")
        print("  r      - Reset parameters to defaults")
        print("  s      - Save current settings")
        print("  q/ESC  - Quit (or click X on window)")
        print("\nTIPS:")
        print("  - Click on the VIDEO area (not sliders) for keyboard controls")
        print("  - Adjust sliders in real-time - changes apply immediately")
        print("  - Watch the middle panel (mask) to see what's being detected\n")
        
        paused = True
        
        while True:
            # Get current parameters from trackbars
            h_low = cv2.getTrackbarPos('H Low', window)
            h_high = cv2.getTrackbarPos('H High', window)
            s_low = cv2.getTrackbarPos('S Low', window)
            s_high = cv2.getTrackbarPos('S High', window)
            v_low = cv2.getTrackbarPos('V Low', window)
            v_high = cv2.getTrackbarPos('V High', window)
            min_area = cv2.getTrackbarPos('Min Area', window)
            frame_pos = cv2.getTrackbarPos('Frame', window)
            
            # Update parameters
            self.lower_green = np.array([h_low, s_low, v_low])
            self.upper_green = np.array([h_high, s_high, v_high])
            self.min_area = min_area
            
            # Seek to frame if trackbar moved
            if frame_pos != self.current_frame:
                self.seek_frame(frame_pos)

            # When paused, we need to seek back to show the same frame
            # When playing, we let the video naturally advance
            if paused:
                # Seek to current frame - cap.read() will then return this frame
                # But CAP_PROP_POS_FRAMES returns position AFTER read, so seek to current-1
                if self.current_frame > 0:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame - 1)
                else:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

            # Read frame (advances position by 1)
            ret, frame = self.cap.read()

            if not ret:
                # Loop back to start
                self.seek_frame(0)
                continue

            # Update current position (this is the frame we just read)
            if paused:
                # Don't update when paused - stay on same frame number
                pass
            else:
                # When playing, update to actual position
                self.current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            
            # Run detection
            annotated, mask, weed_count = self.detect_weeds(frame)
            
            # Create display
            mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            display = np.hstack([frame, mask_bgr, annotated])
            
            # Add info overlay
            info_text = [
                f"Frame: {self.current_frame}/{self.total_frames}",
                f"Weeds: {weed_count}",
                f"HSV: [{h_low},{s_low},{v_low}] - [{h_high},{s_high},{v_high}]",
                f"Min Area: {min_area}",
                "SPACE=play/pause, arrows=seek, s=save, q=quit"
            ]
            
            y_offset = 30
            for text in info_text:
                cv2.putText(display, text, (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                y_offset += 25
            
            # Add playback indicator
            status = "PLAYING" if not paused else "PAUSED"
            cv2.putText(display, status, (display.shape[1]-150, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, 
                       (0, 255, 0) if not paused else (0, 0, 255), 2)
            
            cv2.imshow(window, display)

            # Update frame trackbar (without triggering seek)
            if frame_pos == self.current_frame:
                cv2.setTrackbarPos('Frame', window, self.current_frame)

            # Handle keyboard input - always wait at least 30ms to allow slider updates
            wait_time = 30 if paused else 30
            key = cv2.waitKey(wait_time) & 0xFF

            # Check if window was closed by user (X button) - check AFTER waitKey
            try:
                if cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
                    print("\nWindow closed by user")
                    break
            except:
                # Window was destroyed
                print("\nWindow destroyed")
                break

            # Debug: show key codes when pressed (uncomment to debug keyboard issues)
            # if key != 255:
            #     print(f"Key pressed: {key} (char: {chr(key) if key < 128 else 'N/A'})")

            if key == ord('q') or key == ord('Q') or key == 27:  # q, Q, or ESC
                print("\nQuitting...")
                break
            elif key == ord(' '):
                paused = not paused
            elif key == 83:  # Right arrow
                paused = True
                if self.current_frame < self.total_frames - 1:
                    self.current_frame += 1
                    self.seek_frame(self.current_frame)
            elif key == 81:  # Left arrow
                paused = True
                if self.current_frame > 0:
                    self.current_frame -= 1
                    self.seek_frame(self.current_frame)
            elif key == 82:  # Up arrow
                paused = True
                self.seek_frame(min(self.current_frame + 10, self.total_frames - 1))
            elif key == 84:  # Down arrow
                paused = True
                self.seek_frame(max(self.current_frame - 10, 0))
            elif key == ord('r'):
                # Reset to defaults
                cv2.setTrackbarPos('H Low', window, 35)
                cv2.setTrackbarPos('H High', window, 85)
                cv2.setTrackbarPos('S Low', window, 40)
                cv2.setTrackbarPos('S High', window, 255)
                cv2.setTrackbarPos('V Low', window, 40)
                cv2.setTrackbarPos('V High', window, 255)
                cv2.setTrackbarPos('Min Area', window, 100)
                print("Reset to default parameters")
            elif key == ord('s'):
                self.save_settings()
                print("Settings saved!")

            # Frame advancement happens automatically via cap.read() when not paused
            # No need to manually increment current_frame
        
        self.cap.release()
        cv2.destroyAllWindows()
    
    def save_settings(self):
        """Save current parameters to config file"""
        config = {
            'lower_green': self.lower_green.tolist(),
            'upper_green': self.upper_green.tolist(),
            'min_area': self.min_area,
            'max_area': self.max_area
        }
        
        with open('weed_detector_config.json', 'w') as f:
            json.dump(config, f, indent=4)
        
        print(f"\nConfiguration saved:")
        print(f"  Lower HSV: {self.lower_green}")
        print(f"  Upper HSV: {self.upper_green}")
        print(f"  Min Area: {self.min_area}")

def main():
    if len(sys.argv) < 2:
        print("Video Tuning Tool")
        print("\nUsage:")
        print("  python3 video_tuner.py <video_file.mp4>")
        print("\nThis tool lets you:")
        print("  - Scrub through your video frame by frame")
        print("  - Adjust detection parameters in real-time")
        print("  - See immediate results")
        print("  - Save optimal settings for batch processing")
        return
    
    video_path = sys.argv[1]
    
    try:
        tuner = VideoTuner(video_path)
        tuner.run()
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()