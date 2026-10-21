# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, jsonify, Response
import cv2
import threading
import time
import csv
import os
import datetime
import subprocess
from motor_control import MotorController
from lane_detection import LaneDetector
from pid_controller import PIDController
from picamera2 import Picamera2

app = Flask(__name__)
car = MotorController()
detector = LaneDetector()
pid = PIDController(Kp=0.35, Ki=0.005, Kd=0.08)

picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (640, 480), "format": "RGB888"})
picam2.configure(config)
picam2.start()

pan_angle = 90
tilt_angle = 20
car.set_camera_servo(10, pan_angle, 0.5)
car.set_camera_servo(9, tilt_angle, 0.5)

current_frame = None
is_autonomous = False
current_offset = 0.0
current_manual_cmd = "stop"  # 【新增】記錄當前指令狀態
lock = threading.Lock()

last_heartbeat = time.time()
connection_lost = False
LOG_FILE = "/home/pi/ai_car_project/car_status_log.csv"

# 【更新】加入 Command 欄位
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Mode", "Connection", "Command", "Offset", "Steering", "CPU_Temp(C)"])

def get_cpu_temp():
    try:
        res = subprocess.check_output(['vcgencmd', 'measure_temp']).decode('utf-8')
        return res.replace("temp=", "").replace("'C\n", "")
    except Exception:
        return "0.0"

def camera_and_lane_worker():
    global current_frame, current_offset, is_autonomous, last_heartbeat, connection_lost, current_manual_cmd
    last_log_time = time.time()
    
    while True:
        try:
            frame_rgb = picam2.capture_array()
            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            frame_bgr = cv2.flip(frame_bgr, -1)

            processed_frame, offset = detector.process_frame(frame_bgr)
            current_offset = offset

            if time.time() - last_heartbeat > 1.0:
                if not connection_lost:
                    print("[安全保護] 網頁已斷線或關閉，啟動緊急煞車！")
                    is_autonomous = False
                    current_manual_cmd = "stop"
                    car.stop()
                    connection_lost = True
            else:
                connection_lost = False

            steering = 0.0
            if is_autonomous and not connection_lost:
                current_manual_cmd = "auto_nav"
                steering = pid.update(offset)
                base_speed = 35
                if hasattr(car.robot, 'move_with_offset'):
                    car.robot.move_with_offset(base_speed, int(steering), -int(steering), 0)
                else:
                    if steering > 8: car.right(35)
                    elif steering < -8: car.left(35)
                    else: car.forward(35)

            # 每 1 秒寫入一筆 Log 記錄，加入 Command
            current_time = time.time()
            if current_time - last_log_time >= 1.0:
                with open(LOG_FILE, mode='a', newline='') as f:
                    writer = csv.writer(f)
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    mode_str = "Auto" if is_autonomous else "Manual"
                    conn_str = "Lost" if connection_lost else "OK"
                    temp_str = get_cpu_temp()
                    writer.writerow([timestamp, mode_str, conn_str, current_manual_cmd, round(offset, 2), round(steering, 2), temp_str])
                last_log_time = current_time

            with lock:
                current_frame = processed_frame.copy()
        except Exception as e:
            print(f"Vision loop error: {e}")
        time.sleep(0.03)

threading.Thread(target=camera_and_lane_worker, daemon=True).start()

def generate_frames():
    while True:
        try:
            with lock:
                if current_frame is None:
                    time.sleep(0.01)
                    continue
                ret, buffer = cv2.imencode('.jpg', current_frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.04)
        except GeneratorExit:
            print("Client disconnected stream.")
            break
        except Exception as e:
            break

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_status')
def get_status():
    global last_heartbeat
    last_heartbeat = time.time()
    return jsonify({'autonomous': is_autonomous, 'offset': round(current_offset, 2)})

@app.route('/toggle_auto', methods=['POST'])
def toggle_auto():
    global is_autonomous, last_heartbeat, current_manual_cmd
    last_heartbeat = time.time()
    data = request.get_json() or {}
    is_autonomous = data.get('enable', False)
    if not is_autonomous:
        current_manual_cmd = "stop"
        car.stop()
        pid.reset()
    return jsonify({'status': 'success', 'autonomous': is_autonomous})

@app.route('/control', methods=['POST'])
def control():
    global is_autonomous, last_heartbeat, current_manual_cmd
    last_heartbeat = time.time()
    if is_autonomous: return jsonify({'status': 'ignored', 'msg': 'Auto mode active'})
    
    data = request.get_json() or {}
    command = data.get('command')
    speed = data.get('speed', 35)

    current_manual_cmd = command  # 【新增】更新當前按下的控制指令

    if command == 'forward': car.forward(speed)
    elif command == 'backward': car.backward(speed)
    elif command == 'left': car.left(speed)
    elif command == 'right': car.right(speed)
    elif command == 'stop': car.stop()

    return jsonify({'status': 'success', 'command': command})

@app.route('/camera_control', methods=['POST'])
def camera_control():
    global pan_angle, tilt_angle, last_heartbeat
    last_heartbeat = time.time()
    data = request.get_json() or {}
    direction = data.get('direction')
    step = 5

    if direction == 'cam_up':
        tilt_angle = max(15, tilt_angle - step)
        car.set_camera_servo(9, tilt_angle, 0.05)
    elif direction == 'cam_down':
        tilt_angle = min(70, tilt_angle + step)
        car.set_camera_servo(9, tilt_angle, 0.05)
    elif direction == 'cam_left':
        pan_angle = min(130, pan_angle + step)
        car.set_camera_servo(10, pan_angle, 0.05)
    elif direction == 'cam_right':
        pan_angle = max(50, pan_angle - step)
        car.set_camera_servo(10, pan_angle, 0.05)
    elif direction == 'cam_center':
        pan_angle = 90
        tilt_angle = 20
        car.set_camera_servo(10, pan_angle, 0.3)
        car.set_camera_servo(9, tilt_angle, 0.3)

    return jsonify({'status': 'success', 'pan': pan_angle, 'tilt': tilt_angle})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
