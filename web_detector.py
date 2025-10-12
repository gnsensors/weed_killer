#!/usr/bin/env python3
"""
Web-based weed detector interface
Access from browser: http://localhost:5000
Works great for Chromebook development or headless Pi
"""

from flask import Flask, render_template_string, Response, request, jsonify
import cv2
import numpy as np
import base64
import json

app = Flask(__name__)

class WeedDetector:
    def __init__(self):
        self.lower_green = np.array([35, 40, 40])
        self.upper_green = np.array([85, 255, 255])
        self.min_area = 100
        self.max_area = 50000
        self.camera = None
    
    def detect_weeds(self, frame):
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
            
            detections.append({
                'id': i, 'centroid': (cx, cy),
                'bbox': (x, y, w, h), 'area': int(area)
            })
            
            cv2.rectangle(annotated, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.circle(annotated, (cx, cy), 5, (0, 0, 255), -1)
            cv2.putText(annotated, f"W{i}", (x, y-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return annotated, mask, detections
    
    def get_frame(self):
        if self.camera is None:
            self.camera = cv2.VideoCapture(0)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        ret, frame = self.camera.read()
        if not ret:
            return None, None, []
        
        return self.detect_weeds(frame)

detector = WeedDetector()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Weed Detection System</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 { color: #2c5f2d; }
        .controls {
            background: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .slider-group {
            margin: 15px 0;
        }
        label {
            display: inline-block;
            width: 100px;
            font-weight: bold;
        }
        input[type="range"] {
            width: 300px;
        }
        .value {
            display: inline-block;
            width: 50px;
            text-align: right;
        }
        .video-container {
            display: flex;
            gap: 10px;
            justify-content: center;
            flex-wrap: wrap;
        }
        .video-box {
            background: white;
            padding: 10px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        img {
            max-width: 100%;
            height: auto;
            border: 2px solid #ddd;
        }
        .stats {
            background: #2c5f2d;
            color: white;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
        }
        button {
            background: #2c5f2d;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            margin: 5px;
        }
        button:hover { background: #1e4620; }
        #detections-list {
            max-height: 200px;
            overflow-y: auto;
            background: white;
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <h1>🌱 Weed Detection System</h1>
    
    <div class="stats">
        <h3>Detection Status</h3>
        <div>Weeds Detected: <span id="weed-count">0</span></div>
        <div id="detections-list"></div>
    </div>
    
    <div class="controls">
        <h3>Detection Parameters</h3>
        <div class="slider-group">
            <label>H Low:</label>
            <input type="range" id="h_low" min="0" max="179" value="35" oninput="updateParams()">
            <span class="value" id="h_low_val">35</span>
        </div>
        <div class="slider-group">
            <label>H High:</label>
            <input type="range" id="h_high" min="0" max="179" value="85" oninput="updateParams()">
            <span class="value" id="h_high_val">85</span>
        </div>
        <div class="slider-group">
            <label>S Low:</label>
            <input type="range" id="s_low" min="0" max="255" value="40" oninput="updateParams()">
            <span class="value" id="s_low_val">40</span>
        </div>
        <div class="slider-group">
            <label>S High:</label>
            <input type="range" id="s_high" min="0" max="255" value="255" oninput="updateParams()">
            <span class="value" id="s_high_val">255</span>
        </div>
        <div class="slider-group">
            <label>V Low:</label>
            <input type="range" id="v_low" min="0" max="255" value="40" oninput="updateParams()">
            <span class="value" id="v_low_val">40</span>
        </div>
        <div class="slider-group">
            <label>V High:</label>
            <input type="range" id="v_high" min="0" max="255" value="255" oninput="updateParams()">
            <span class="value" id="v_high_val">255</span>
        </div>
        <div class="slider-group">
            <label>Min Area:</label>
            <input type="range" id="min_area" min="10" max="1000" value="100" oninput="updateParams()">
            <span class="value" id="min_area_val">100</span>
        </div>
        <button onclick="saveParams()">Save Settings</button>
        <button onclick="resetParams()">Reset to Defaults</button>
    </div>
    
    <div class="video-container">
        <div class="video-box">
            <h3>Detection View</h3>
            <img id="video-feed" src="/video_feed" width="640" height="480">
        </div>
    </div>
    
    <script>
        function updateParams() {
            const params = {
                h_low: document.getElementById('h_low').value,
                h_high: document.getElementById('h_high').value,
                s_low: document.getElementById('s_low').value,
                s_high: document.getElementById('s_high').value,
                v_low: document.getElementById('v_low').value,
                v_high: document.getElementById('v_high').value,
                min_area: document.getElementById('min_area').value
            };
            
            // Update displayed values
            for (let key in params) {
                document.getElementById(key + '_val').textContent = params[key];
            }
            
            // Send to server
            fetch('/update_params', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(params)
            });
        }
        
        function saveParams() {
            fetch('/save_params', {method: 'POST'})
                .then(response => response.json())
                .then(data => alert(data.message));
        }
        
        function resetParams() {
            document.getElementById('h_low').value = 35;
            document.getElementById('h_high').value = 85;
            document.getElementById('s_low').value = 40;
            document.getElementById('s_high').value = 255;
            document.getElementById('v_low').value = 40;
            document.getElementById('v_high').value = 255;
            document.getElementById('min_area').value = 100;
            updateParams();
        }
        
        // Update detection count periodically
        setInterval(() => {
            fetch('/get_detections')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('weed-count').textContent = data.count;
                    
                    let list = '<ul>';
                    data.detections.forEach(det => {
                        list += `<li>Weed ${det.id}: ${det.area}px at (${det.centroid[0]}, ${det.centroid[1]})</li>`;
                    });
                    list += '</ul>';
                    document.getElementById('detections-list').innerHTML = list;
                });
        }, 500);
        
        // Refresh video feed
        setInterval(() => {
            document.getElementById('video-feed').src = '/video_feed?' + new Date().getTime();
        }, 100);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/video_feed')
def video_feed():
    annotated, mask, detections = detector.get_frame()
    if annotated is None:
        return "Camera Error", 500
    
    _, buffer = cv2.imencode('.jpg', annotated)
    return Response(buffer.tobytes(), mimetype='image/jpeg')

@app.route('/get_detections')
def get_detections():
    annotated, mask, detections = detector.get_frame()
    return jsonify({'count': len(detections), 'detections': detections})

@app.route('/update_params', methods=['POST'])
def update_params():
    params = request.json
    detector.lower_green = np.array([
        int(params['h_low']),
        int(params['s_low']),
        int(params['v_low'])
    ])
    detector.upper_green = np.array([
        int(params['h_high']),
        int(params['s_high']),
        int(params['v_high'])
    ])
    detector.min_area = int(params['min_area'])
    return jsonify({'status': 'ok'})

@app.route('/save_params', methods=['POST'])
def save_params():
    config = {
        'lower_green': detector.lower_green.tolist(),
        'upper_green': detector.upper_green.tolist(),
        'min_area': detector.min_area
    }
    with open('weed_detector_config.json', 'w') as f:
        json.dump(config, f, indent=4)
    return jsonify({'message': 'Settings saved!'})

if __name__ == '__main__':
    print("\n=== Web-Based Weed Detector ===")
    print("Starting server...")
    print("Open browser to: http://localhost:5000")
    print("Or from another device: http://<your-ip>:5000")
    print("\nPress Ctrl+C to stop\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
