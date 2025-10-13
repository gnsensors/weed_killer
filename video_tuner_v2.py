#!/usr/bin/env python3
"""
Interactive tuning tool for video weed detection - Refactored with state machine
Cleaner architecture with separated concerns: Focus, Input, Frame state
"""

import cv2
import numpy as np
import json
import sys
from enum import Enum


class PlaybackState(Enum):
    """Video playback states"""
    PAUSED = "PAUSED"
    PLAYING = "PLAYING"


class FrameManager:
    """Manages frame position and seeking logic"""

    def __init__(self, video_capture):
        self.cap = video_capture
        self.current_frame = 0
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)

    def seek_to(self, frame_number):
        """Seek to specific frame"""
        frame_number = max(0, min(frame_number, self.total_frames - 1))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        self.current_frame = frame_number
        return frame_number

    def advance(self, delta=1):
        """Advance frame by delta (can be negative)"""
        new_frame = self.current_frame + delta
        return self.seek_to(new_frame)

    def read_frame(self, playback_state):
        """
        Read next frame based on playback state
        Returns: (success, frame, current_frame_number)
        """
        if playback_state == PlaybackState.PAUSED:
            # Stay on current frame
            self.seek_to(self.current_frame)

        ret, frame = self.cap.read()

        if not ret:
            # Loop back to start
            self.seek_to(0)
            ret, frame = self.cap.read()

        # Update position after read
        if playback_state == PlaybackState.PLAYING:
            self.current_frame += 1
            if self.current_frame >= self.total_frames:
                self.current_frame = 0

        return ret, frame, self.current_frame


class InputHandler:
    """Handles keyboard and trackbar input"""

    def __init__(self, window_name):
        self.window_name = window_name
        self.last_trackbar_frame = 0

    def poll_keyboard(self, wait_ms=30):
        """Poll for keyboard input. Returns key code (255 = no key)"""
        return cv2.waitKey(wait_ms) & 0xFF

    def get_trackbar_values(self):
        """Get all trackbar values as dict"""
        return {
            'h_low': cv2.getTrackbarPos('H Low', self.window_name),
            'h_high': cv2.getTrackbarPos('H High', self.window_name),
            's_low': cv2.getTrackbarPos('S Low', self.window_name),
            's_high': cv2.getTrackbarPos('S High', self.window_name),
            'v_low': cv2.getTrackbarPos('V Low', self.window_name),
            'v_high': cv2.getTrackbarPos('V High', self.window_name),
            'min_area': cv2.getTrackbarPos('Min Area', self.window_name),
            'frame': cv2.getTrackbarPos('Frame', self.window_name)
        }

    def update_frame_trackbar(self, frame_number):
        """Update frame trackbar position"""
        cv2.setTrackbarPos('Frame', self.window_name, frame_number)
        self.last_trackbar_frame = frame_number

    def was_frame_trackbar_moved_by_user(self, current_trackbar_value):
        """Check if user manually moved frame trackbar (vs programmatic update)"""
        if current_trackbar_value != self.last_trackbar_frame:
            # Trackbar changed - was it user or us?
            return True
        return False

    def reset_trackbars_to_defaults(self):
        """Reset all detection parameter trackbars to defaults"""
        cv2.setTrackbarPos('H Low', self.window_name, 35)
        cv2.setTrackbarPos('H High', self.window_name, 85)
        cv2.setTrackbarPos('S Low', self.window_name, 40)
        cv2.setTrackbarPos('S High', self.window_name, 255)
        cv2.setTrackbarPos('V Low', self.window_name, 40)
        cv2.setTrackbarPos('V High', self.window_name, 255)
        cv2.setTrackbarPos('Min Area', self.window_name, 100)


class FocusManager:
    """Manages window focus and keyboard capture"""

    def __init__(self, window_name):
        self.window_name = window_name
        self.has_focus = True  # Assume focus initially

    def check_window_alive(self):
        """Check if window is still open"""
        try:
            if cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) < 1:
                return False
            return True
        except:
            return False

    def update_focus_hint(self):
        """Could be extended to visually indicate focus state"""
        pass


class VideoTunerStateMachine:
    """Main state machine for video tuning"""

    def __init__(self, video_path):
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)

        if not self.cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")

        # State components
        self.frame_mgr = FrameManager(self.cap)
        self.playback_state = PlaybackState.PAUSED

        # Detection parameters
        self.lower_green = np.array([35, 40, 40])
        self.upper_green = np.array([85, 255, 255])
        self.min_area = 100
        self.max_area = 50000

        # UI setup
        self.window_name = "Video Tuner - Click video to enable keys"
        self._setup_window()

        self.input_handler = InputHandler(self.window_name)
        self.focus_mgr = FocusManager(self.window_name)

        self.running = True

    def _setup_window(self):
        """Initialize window and trackbars"""
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, 1600, 900)

        # Create trackbars
        cv2.createTrackbar('H Low', self.window_name, self.lower_green[0], 179, lambda x: None)
        cv2.createTrackbar('H High', self.window_name, self.upper_green[0], 179, lambda x: None)
        cv2.createTrackbar('S Low', self.window_name, self.lower_green[1], 255, lambda x: None)
        cv2.createTrackbar('S High', self.window_name, self.upper_green[1], 255, lambda x: None)
        cv2.createTrackbar('V Low', self.window_name, self.lower_green[2], 255, lambda x: None)
        cv2.createTrackbar('V High', self.window_name, self.upper_green[2], 255, lambda x: None)
        cv2.createTrackbar('Min Area', self.window_name, self.min_area, 2000, lambda x: None)
        cv2.createTrackbar('Frame', self.window_name, 0, self.frame_mgr.total_frames - 1, lambda x: None)

    def detect_weeds(self, frame):
        """Run detection on frame"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_green, self.upper_green)

        kernel = np.ones((5, 5), np.uint8)
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
                cx, cy = x + w // 2, y + h // 2

            cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.circle(annotated, (cx, cy), 5, (0, 0, 255), -1)
            cv2.putText(annotated, f"{int(area)}", (x, y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

        return annotated, mask, weed_count

    def update_detection_params(self, trackbar_values):
        """Update detection parameters from trackbars"""
        self.lower_green = np.array([trackbar_values['h_low'],
                                     trackbar_values['s_low'],
                                     trackbar_values['v_low']])
        self.upper_green = np.array([trackbar_values['h_high'],
                                      trackbar_values['s_high'],
                                      trackbar_values['v_high']])
        self.min_area = trackbar_values['min_area']

    def handle_keyboard_input(self, key):
        """
        Process keyboard input and update state
        Returns: True if handled, False if not recognized
        """
        if key == 255:
            return False  # No key pressed

        # Quit commands
        if key == 27 or key == ord('q') or key == ord('Q'):
            print("\nQuitting...")
            self.running = False
            return True

        # Playback control
        elif key == ord(' '):
            self.playback_state = (PlaybackState.PLAYING if self.playback_state == PlaybackState.PAUSED
                                  else PlaybackState.PAUSED)
            print(f"Playback: {self.playback_state.value}")
            return True

        # Frame navigation - always pause when navigating
        elif key == ord('d') or key == ord('D') or key == 83:  # D or RIGHT arrow
            self.playback_state = PlaybackState.PAUSED
            self.frame_mgr.advance(1)
            return True

        elif key == ord('a') or key == ord('A') or key == 81:  # A or LEFT arrow
            self.playback_state = PlaybackState.PAUSED
            self.frame_mgr.advance(-1)
            return True

        elif key == ord('w') or key == ord('W') or key == 82:  # W or UP arrow
            self.playback_state = PlaybackState.PAUSED
            self.frame_mgr.advance(10)
            return True

        elif key == ord('s') or key == ord('S') or key == 84:  # S or DOWN arrow
            self.playback_state = PlaybackState.PAUSED
            self.frame_mgr.advance(-10)
            return True

        # Parameter management
        elif key == ord('p') or key == ord('P'):
            self.save_settings()
            print("Settings saved!")
            return True

        elif key == ord('r') or key == ord('R'):
            self.input_handler.reset_trackbars_to_defaults()
            print("Reset to default parameters")
            return True

        return False

    def handle_frame_trackbar(self, trackbar_frame_value):
        """Handle user moving the frame trackbar"""
        if self.input_handler.was_frame_trackbar_moved_by_user(trackbar_frame_value):
            if trackbar_frame_value != self.frame_mgr.current_frame:
                # User moved trackbar - seek to that frame
                self.frame_mgr.seek_to(trackbar_frame_value)
                self.playback_state = PlaybackState.PAUSED
                self.input_handler.last_trackbar_frame = trackbar_frame_value

    def render_display(self, frame, mask, weed_count, trackbar_values):
        """Create display with all panels and overlays"""
        mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        display = np.hstack([frame, mask_bgr, mask_bgr])  # Three panels

        # Add info overlay
        info_text = [
            f"Frame: {self.frame_mgr.current_frame}/{self.frame_mgr.total_frames}",
            f"Weeds: {weed_count}",
            f"HSV: [{trackbar_values['h_low']},{trackbar_values['s_low']},{trackbar_values['v_low']}] - "
            f"[{trackbar_values['h_high']},{trackbar_values['s_high']},{trackbar_values['v_high']}]",
            f"Min Area: {trackbar_values['min_area']}",
            "SPACE=play/pause | WASD=navigate | P=save | R=reset | Q=quit"
        ]

        y_offset = 30
        for text in info_text:
            cv2.putText(display, text, (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2,
                       cv2.LINE_AA)
            y_offset += 25

        # Playback indicator
        status = self.playback_state.value
        color = (0, 255, 0) if self.playback_state == PlaybackState.PLAYING else (0, 0, 255)
        cv2.putText(display, status, (display.shape[1] - 200, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)

        return display

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

    def run(self):
        """Main state machine loop"""
        print("\n=== Video Tuning Mode (Refactored) ===")
        print("\n*** Click on VIDEO IMAGE to enable keyboard controls ***\n")
        print("Controls:")
        print("  SPACE      - Play/Pause")
        print("  W/A/S/D    - Navigate frames (up/left/down/right)")
        print("  P          - Save parameters")
        print("  R          - Reset to defaults")
        print("  Q/ESC      - Quit\n")

        while self.running:
            # Check if window still exists
            if not self.focus_mgr.check_window_alive():
                print("\nWindow closed")
                break

            # Get trackbar values
            trackbar_values = self.input_handler.get_trackbar_values()

            # Update detection parameters
            self.update_detection_params(trackbar_values)

            # Handle frame trackbar movement
            self.handle_frame_trackbar(trackbar_values['frame'])

            # Read frame based on current playback state
            ret, frame, current_frame = self.frame_mgr.read_frame(self.playback_state)

            if not ret:
                print("Failed to read frame")
                break

            # Run detection
            annotated, mask, weed_count = self.detect_weeds(frame)

            # Render display
            display = self.render_display(annotated, mask, weed_count, trackbar_values)

            # Show display
            cv2.imshow(self.window_name, display)

            # Update frame trackbar
            self.input_handler.update_frame_trackbar(self.frame_mgr.current_frame)

            # Poll keyboard
            key = self.input_handler.poll_keyboard(30)

            # Handle keyboard input
            self.handle_keyboard_input(key)

        # Cleanup
        self.cap.release()
        cv2.destroyAllWindows()


def main():
    if len(sys.argv) < 2:
        print("Video Tuning Tool (Refactored)")
        print("\nUsage:")
        print("  python3 video_tuner_v2.py <video_file.mp4>")
        return

    video_path = sys.argv[1]

    try:
        tuner = VideoTunerStateMachine(video_path)
        tuner.run()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
