#!/usr/bin/env python3
"""
Stream Manager - Handles video stream connections and reconnection logic
Supports RTSP, HTTP/MJPEG streams from IP cameras
"""

import cv2
import time
import requests
from typing import Optional, Tuple


class StreamManager:
    """Manages video stream connections with automatic reconnection"""

    def __init__(self, stream_url: str, buffer_size: int = 1):
        """
        Initialize stream manager

        Args:
            stream_url: URL of video stream (RTSP or HTTP)
            buffer_size: OpenCV buffer size (1 = minimal latency)
        """
        self.stream_url = stream_url
        self.buffer_size = buffer_size
        self.cap: Optional[cv2.VideoCapture] = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 1.0  # seconds
        self.is_connected = False
        self.last_frame_time = time.time()
        self.frame_timeout = 5.0  # seconds

    def connect(self) -> bool:
        """
        Connect to video stream

        Returns:
            True if connection successful, False otherwise
        """
        print(f"Connecting to stream: {self.stream_url}")

        try:
            self.cap = cv2.VideoCapture(self.stream_url)

            if not self.cap.isOpened():
                print("Failed to open stream")
                return False

            # Set buffer size to minimize latency
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, self.buffer_size)

            # Test read a frame
            ret, frame = self.cap.read()
            if not ret or frame is None:
                print("Failed to read test frame")
                self.cap.release()
                return False

            self.is_connected = True
            self.reconnect_attempts = 0
            self.last_frame_time = time.time()

            # Get stream properties
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.cap.get(cv2.CAP_PROP_FPS)

            print(f"✓ Connected successfully")
            print(f"  Resolution: {width}x{height}")
            print(f"  FPS: {fps if fps > 0 else 'Unknown'}")

            return True

        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def read_frame(self) -> Tuple[bool, Optional[any]]:
        """
        Read a frame from the stream

        Returns:
            (success, frame) tuple
        """
        if not self.is_connected or self.cap is None:
            return False, None

        try:
            ret, frame = self.cap.read()

            if ret and frame is not None:
                self.last_frame_time = time.time()
                return True, frame
            else:
                # Check if stream has timed out
                if time.time() - self.last_frame_time > self.frame_timeout:
                    print("Stream timeout - no frames received")
                    self.is_connected = False
                return False, None

        except Exception as e:
            print(f"Error reading frame: {e}")
            self.is_connected = False
            return False, None

    def reconnect(self) -> bool:
        """
        Attempt to reconnect to stream

        Returns:
            True if reconnection successful
        """
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            print(f"Max reconnection attempts ({self.max_reconnect_attempts}) reached")
            return False

        self.reconnect_attempts += 1
        print(f"\nReconnection attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}")

        # Release old connection
        self.disconnect()

        # Exponential backoff
        delay = self.reconnect_delay * (2 ** (self.reconnect_attempts - 1))
        print(f"Waiting {delay:.1f} seconds before reconnecting...")
        time.sleep(delay)

        return self.connect()

    def disconnect(self):
        """Disconnect from stream and cleanup"""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.is_connected = False

    def get_stream_info(self) -> dict:
        """Get stream properties"""
        if not self.is_connected or self.cap is None:
            return {}

        return {
            'width': int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'fps': self.cap.get(cv2.CAP_PROP_FPS),
            'backend': self.cap.getBackendName()
        }

    @staticmethod
    def test_url(url: str, timeout: float = 5.0) -> bool:
        """
        Test if a URL is reachable

        Args:
            url: URL to test
            timeout: Request timeout in seconds

        Returns:
            True if URL responds
        """
        try:
            # For HTTP streams, try a HEAD request
            if url.startswith('http'):
                response = requests.head(url, timeout=timeout, allow_redirects=True)
                return response.status_code == 200
            else:
                # For RTSP, try opening with OpenCV
                cap = cv2.VideoCapture(url)
                is_open = cap.isOpened()
                cap.release()
                return is_open
        except Exception as e:
            print(f"URL test failed: {e}")
            return False


class FPSCounter:
    """Track frames per second for performance monitoring"""

    def __init__(self, window_size: int = 30):
        """
        Initialize FPS counter

        Args:
            window_size: Number of frames to average over
        """
        self.window_size = window_size
        self.frame_times = []
        self.last_time = time.time()

    def tick(self):
        """Record a frame timestamp"""
        current_time = time.time()
        self.frame_times.append(current_time)

        # Keep only recent frames
        if len(self.frame_times) > self.window_size:
            self.frame_times.pop(0)

    def get_fps(self) -> float:
        """
        Get current FPS

        Returns:
            Frames per second (averaged over window)
        """
        if len(self.frame_times) < 2:
            return 0.0

        time_span = self.frame_times[-1] - self.frame_times[0]
        if time_span == 0:
            return 0.0

        return (len(self.frame_times) - 1) / time_span

    def get_latency(self) -> float:
        """
        Get average frame latency

        Returns:
            Milliseconds per frame
        """
        fps = self.get_fps()
        if fps == 0:
            return 0.0
        return 1000.0 / fps


# Test code
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Stream Manager Test")
        print("\nUsage:")
        print("  python3 stream_manager.py <stream_url>")
        print("\nExample:")
        print("  python3 stream_manager.py http://192.168.1.100:8080/video")
        sys.exit(1)

    url = sys.argv[1]

    print("Testing stream URL...")
    if not StreamManager.test_url(url):
        print("✗ URL is not reachable or invalid")
        sys.exit(1)

    print("✓ URL is reachable\n")

    # Test connection
    manager = StreamManager(url)

    if not manager.connect():
        print("✗ Failed to connect to stream")
        sys.exit(1)

    print("\nStream info:", manager.get_stream_info())

    print("\nReading 10 test frames...")
    fps_counter = FPSCounter()

    for i in range(10):
        ret, frame = manager.read_frame()
        if ret:
            fps_counter.tick()
            print(f"  Frame {i+1}: {frame.shape} - FPS: {fps_counter.get_fps():.1f}")
        else:
            print(f"  Frame {i+1}: Failed to read")

        time.sleep(0.1)

    manager.disconnect()
    print("\n✓ Test complete")
