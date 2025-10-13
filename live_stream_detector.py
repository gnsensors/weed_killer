#!/usr/bin/env python3
"""
Live Stream Weed Detector
Process video stream from IP camera (Android phone) for real-time weed detection
"""

import cv2
import numpy as np
import json
import sys
import time
from stream_manager import StreamManager, FPSCounter
from network_discovery import NetworkDiscovery, manual_entry


class LiveStreamDetector:
    """Real-time weed detection from video stream"""

    def __init__(self, stream_url: str):
        """
        Initialize live stream detector

        Args:
            stream_url: URL of video stream
        """
        self.stream_url = stream_url
        self.stream_mgr = StreamManager(stream_url)

        # Detection parameters - load from config if exists
        self.load_settings()

        # Performance tracking
        self.fps_counter = FPSCounter(window_size=30)
        self.frame_count = 0
        self.detection_count = 0

        # Display settings
        self.show_display = True
        self.display_scale = 1.0

    def load_settings(self, filename="weed_detector_config.json"):
        """Load detection parameters from config file"""
        try:
            with open(filename, 'r') as f:
                config = json.load(f)
            self.lower_green = np.array(config['lower_green'])
            self.upper_green = np.array(config['upper_green'])
            self.min_area = config['min_area']
            self.max_area = config['max_area']
            print(f"✓ Loaded configuration from {filename}")
        except FileNotFoundError:
            print("No config file found, using defaults")
            self.lower_green = np.array([35, 40, 40])
            self.upper_green = np.array([85, 255, 255])
            self.min_area = 100
            self.max_area = 50000

    def detect_weeds(self, frame):
        """
        Detect green objects in frame

        Returns:
            (annotated_frame, weed_count, detections_list)
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_green, self.upper_green)

        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        annotated = frame.copy()
        detections = []

        for contour in contours:
            area = cv2.contourArea(contour)

            if area < self.min_area or area > self.max_area:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
            else:
                cx, cy = x + w // 2, y + h // 2

            detection = {
                'centroid': (cx, cy),
                'bbox': (x, y, w, h),
                'area': int(area)
            }
            detections.append(detection)

            # Draw on annotated image
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.circle(annotated, (cx, cy), 5, (0, 0, 255), -1)
            cv2.putText(annotated, f"{int(area)}px", (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        return annotated, len(detections), detections

    def add_overlay_info(self, frame, weed_count):
        """Add FPS and detection info overlay to frame"""
        h, w = frame.shape[:2]

        # Semi-transparent overlay bar
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 80), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.3, frame, 0.7, 0)

        # FPS and stats
        fps = self.fps_counter.get_fps()
        latency = self.fps_counter.get_latency()

        info_text = [
            f"FPS: {fps:.1f}",
            f"Latency: {latency:.0f}ms",
            f"Weeds: {weed_count}",
            f"Frames: {self.frame_count}",
        ]

        y_offset = 25
        for text in info_text:
            cv2.putText(frame, text, (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y_offset += 20

        # Status indicator (green = good FPS)
        color = (0, 255, 0) if fps >= 15 else (0, 165, 255) if fps >= 10 else (0, 0, 255)
        cv2.circle(frame, (w - 20, 20), 10, color, -1)

        # Instructions
        cv2.putText(frame, "Press Q to quit | S to save config", (10, h - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        return frame

    def run(self, headless=False):
        """
        Run live detection

        Args:
            headless: If True, don't show display (for SSH/remote)
        """
        print("\n=== Live Stream Weed Detector ===")
        print(f"Stream: {self.stream_url}\n")

        # Connect to stream
        if not self.stream_mgr.connect():
            print("✗ Failed to connect to stream")
            print("\nTroubleshooting:")
            print("  1. Check phone IP camera app is running")
            print("  2. Verify URL is correct")
            print("  3. Ensure both devices are on same WiFi")
            return

        print(f"\n✓ Stream connected")
        print("Starting detection...\n")

        if not headless:
            window_name = "Live Weed Detection (Q=quit, S=save)"
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

        try:
            while True:
                # Read frame
                ret, frame = self.stream_mgr.read_frame()

                if not ret:
                    print("Lost connection to stream, attempting to reconnect...")
                    if not self.stream_mgr.reconnect():
                        print("✗ Reconnection failed")
                        break
                    continue

                self.frame_count += 1
                self.fps_counter.tick()

                # Run detection
                annotated, weed_count, detections = self.detect_weeds(frame)

                if weed_count > 0:
                    self.detection_count += 1

                # Add overlay
                display = self.add_overlay_info(annotated, weed_count)

                # Show display
                if not headless:
                    cv2.imshow(window_name, display)

                    # Handle keyboard
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q') or key == ord('Q') or key == 27:
                        print("\nQuitting...")
                        break
                    elif key == ord('s') or key == ord('S'):
                        self.save_settings()
                        print("Settings saved")

                    # Check window closed
                    try:
                        if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                            break
                    except:
                        break

                # Print periodic stats
                if self.frame_count % 100 == 0:
                    fps = self.fps_counter.get_fps()
                    detection_rate = (self.detection_count / self.frame_count) * 100
                    print(f"Frame {self.frame_count}: FPS={fps:.1f}, "
                          f"Weeds detected in {detection_rate:.1f}% of frames")

        except KeyboardInterrupt:
            print("\n\nInterrupted by user")

        finally:
            # Cleanup
            self.stream_mgr.disconnect()
            if not headless:
                cv2.destroyAllWindows()

            # Final stats
            print("\n=== Session Summary ===")
            print(f"Total frames processed: {self.frame_count}")
            print(f"Frames with weeds: {self.detection_count}")
            if self.frame_count > 0:
                detection_rate = (self.detection_count / self.frame_count) * 100
                print(f"Detection rate: {detection_rate:.1f}%")
            avg_fps = self.fps_counter.get_fps()
            print(f"Average FPS: {avg_fps:.1f}")

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


def main():
    """Main entry point with argument parsing"""
    import argparse

    parser = argparse.ArgumentParser(description='Live Stream Weed Detector')
    parser.add_argument('--url', type=str, help='Stream URL (e.g., http://192.168.1.100:8080/video)')
    parser.add_argument('--discover', action='store_true', help='Scan network for cameras')
    parser.add_argument('--quick', action='store_true', help='Quick network scan')
    parser.add_argument('--manual', action='store_true', help='Manually enter URL')
    parser.add_argument('--headless', action='store_true', help='Run without display (for SSH)')

    args = parser.parse_args()

    stream_url = None

    # Handle different input modes
    if args.url:
        stream_url = args.url

    elif args.discover:
        print("Scanning network for IP cameras...")
        discovery = NetworkDiscovery()
        cameras = discovery.scan_network()
        discovery.print_results()

        if cameras:
            print("Which camera would you like to use?")
            choice = input("Enter number (or 'q' to quit): ").strip()
            if choice.lower() == 'q':
                return

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(cameras):
                    stream_url = cameras[idx]['urls'][0]
                else:
                    print("Invalid choice")
                    return
            except ValueError:
                print("Invalid input")
                return
        else:
            print("\nNo cameras found. Try manual entry:")
            stream_url = manual_entry()

    elif args.quick:
        print("Quick scanning network...")
        discovery = NetworkDiscovery()
        urls = discovery.quick_scan()

        if urls:
            print(f"\nFound {len(urls)} possible stream(s):")
            for i, url in enumerate(urls, 1):
                print(f"  {i}. {url}")

            choice = input("\nEnter number to use (or 'q' to quit): ").strip()
            if choice.lower() == 'q':
                return

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(urls):
                    stream_url = urls[idx]
            except ValueError:
                pass

        if not stream_url:
            stream_url = manual_entry()

    elif args.manual:
        stream_url = manual_entry()

    else:
        # No arguments - show help
        parser.print_help()
        print("\n=== Quick Start ===")
        print("1. Start IP camera app on your Android phone")
        print("2. Note the URL shown in the app (e.g., http://192.168.1.100:8080/video)")
        print("3. Run one of:")
        print("   python3 live_stream_detector.py --url <URL>")
        print("   python3 live_stream_detector.py --discover")
        print("   python3 live_stream_detector.py --quick")
        print("   python3 live_stream_detector.py --manual")
        return

    if not stream_url:
        print("No stream URL specified")
        return

    # Run detector
    detector = LiveStreamDetector(stream_url)
    detector.run(headless=args.headless)


if __name__ == "__main__":
    main()
