#!/usr/bin/env python3
"""
Network Discovery - Find IP cameras on local network
Scans common ports and tests for video streams
"""

import socket
import requests
import concurrent.futures
from typing import List, Dict
import ipaddress


class NetworkDiscovery:
    """Discover IP cameras on local network"""

    # Common IP camera ports
    COMMON_PORTS = [8080, 8081, 4747, 8888, 554]  # HTTP and RTSP

    # Common camera endpoints
    COMMON_ENDPOINTS = [
        '/video',
        '/videofeed',
        '/video.mjpeg',
        '/cam',
        '/stream',
        '/mjpeg',
    ]

    def __init__(self):
        self.discovered_cameras = []

    def get_local_network(self) -> str:
        """
        Get local network IP range

        Returns:
            Network CIDR (e.g., "192.168.1.0/24")
        """
        try:
            # Get local IP by connecting to external host (doesn't actually send data)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()

            # Assume /24 subnet
            network = '.'.join(local_ip.split('.')[:-1]) + '.0/24'
            return network

        except Exception as e:
            print(f"Error detecting local network: {e}")
            return "192.168.1.0/24"  # Default fallback

    def scan_host(self, ip: str, port: int, timeout: float = 1.0) -> List[str]:
        """
        Scan a single host:port for camera endpoints

        Args:
            ip: IP address to scan
            port: Port to check
            timeout: Connection timeout

        Returns:
            List of working stream URLs
        """
        working_urls = []

        # Test each common endpoint
        for endpoint in self.COMMON_ENDPOINTS:
            url = f"http://{ip}:{port}{endpoint}"

            try:
                response = requests.head(url, timeout=timeout, allow_redirects=True)
                if response.status_code == 200:
                    # Check if it looks like a video stream
                    content_type = response.headers.get('Content-Type', '')
                    if 'video' in content_type or 'mjpeg' in content_type or 'octet-stream' in content_type:
                        working_urls.append(url)
                        print(f"  ✓ Found: {url}")

            except requests.exceptions.RequestException:
                # Endpoint not reachable, skip silently
                pass

        # Also test RTSP if port 554
        if port == 554:
            rtsp_url = f"rtsp://{ip}:{port}/stream"
            working_urls.append(rtsp_url)  # Add optimistically (can't easily test RTSP)

        return working_urls

    def scan_network(self, network_range: str = None, max_workers: int = 20) -> List[Dict]:
        """
        Scan local network for IP cameras

        Args:
            network_range: CIDR notation (e.g., "192.168.1.0/24"), auto-detect if None
            max_workers: Number of concurrent threads

        Returns:
            List of discovered cameras with URLs
        """
        if network_range is None:
            network_range = self.get_local_network()

        print(f"\nScanning network: {network_range}")
        print(f"Looking for cameras on ports: {self.COMMON_PORTS}")
        print("This may take 1-2 minutes...\n")

        discovered = []
        network = ipaddress.ip_network(network_range, strict=False)

        # Create list of (ip, port) tuples to scan
        scan_targets = []
        for ip in network.hosts():
            for port in self.COMMON_PORTS:
                scan_targets.append((str(ip), port))

        # Scan in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_target = {
                executor.submit(self.scan_host, ip, port): (ip, port)
                for ip, port in scan_targets
            }

            for future in concurrent.futures.as_completed(future_to_target):
                ip, port = future_to_target[future]
                try:
                    urls = future.result()
                    if urls:
                        discovered.append({
                            'ip': ip,
                            'port': port,
                            'urls': urls
                        })
                except Exception as e:
                    pass  # Ignore errors

        self.discovered_cameras = discovered
        return discovered

    def quick_scan(self, subnet: str = None, timeout: float = 0.5) -> List[str]:
        """
        Quick scan for active hosts only (no endpoint testing)

        Args:
            subnet: Network subnet (e.g., "192.168.1"), auto-detect if None
            timeout: Socket timeout

        Returns:
            List of URLs to try
        """
        if subnet is None:
            network = self.get_local_network()
            subnet = '.'.join(network.split('.')[:3])

        print(f"\nQuick scan of {subnet}.x on common ports...")

        active_hosts = []

        # Scan only first 50 IPs and most common ports
        for i in range(1, 50):
            ip = f"{subnet}.{i}"
            for port in [8080, 8081]:  # Most common ports
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((ip, port))
                sock.close()

                if result == 0:
                    # Port is open - generate likely URLs
                    for endpoint in ['/video', '/videofeed']:
                        url = f"http://{ip}:{port}{endpoint}"
                        active_hosts.append(url)
                        print(f"  Found open port: {ip}:{port}")

        return active_hosts

    def print_results(self):
        """Print discovered cameras in readable format"""
        if not self.discovered_cameras:
            print("\n✗ No cameras found on network")
            print("\nTroubleshooting:")
            print("  1. Ensure phone/camera is on same WiFi network")
            print("  2. Start the IP camera app on your phone")
            print("  3. Check the app shows a server URL")
            print("  4. Try manually entering the URL")
            return

        print(f"\n✓ Found {len(self.discovered_cameras)} camera(s):\n")

        for i, camera in enumerate(self.discovered_cameras, 1):
            print(f"{i}. {camera['ip']}:{camera['port']}")
            for url in camera['urls']:
                print(f"   {url}")
            print()


def manual_entry() -> str:
    """Prompt user to manually enter stream URL"""
    print("\n=== Manual URL Entry ===")
    print("Enter the stream URL from your IP camera app")
    print("Examples:")
    print("  http://192.168.1.100:8080/video")
    print("  rtsp://192.168.1.100:8080/stream")
    print()

    url = input("Stream URL: ").strip()
    return url


# Test/CLI interface
if __name__ == "__main__":
    import sys

    print("=== IP Camera Network Discovery ===")

    discovery = NetworkDiscovery()

    if "--quick" in sys.argv:
        # Quick scan
        urls = discovery.quick_scan()
        if urls:
            print(f"\n✓ Found {len(urls)} possible stream URL(s):")
            for url in urls:
                print(f"  {url}")
        else:
            print("\n✗ No cameras found")

    elif "--manual" in sys.argv:
        # Manual entry
        url = manual_entry()
        print(f"\nYou entered: {url}")

        # Test URL
        print("Testing URL...")
        from stream_manager import StreamManager
        if StreamManager.test_url(url):
            print("✓ URL is reachable!")
        else:
            print("✗ URL is not reachable")

    else:
        # Full scan
        print("\nOptions:")
        print("  1. Full network scan (slow but thorough)")
        print("  2. Quick scan (fast, common ports only)")
        print("  3. Manual entry")
        print()

        choice = input("Choose (1/2/3): ").strip()

        if choice == "1":
            cameras = discovery.scan_network()
            discovery.print_results()

        elif choice == "2":
            urls = discovery.quick_scan()
            if urls:
                print(f"\n✓ Found {len(urls)} possible stream(s):")
                for url in urls:
                    print(f"  {url}")
            else:
                print("\n✗ No cameras found")

        elif choice == "3":
            url = manual_entry()
            print(f"\nYou entered: {url}")
