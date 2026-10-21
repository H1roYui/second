# -*- coding: utf-8 -*-
import sys
import threading
sys.path.append('/home/pi')

try:
    from LOBOROBOT2 import LOBOROBOT
except ImportError:
    LOBOROBOT = None

class MotorController:
    def __init__(self):
        self.lock = threading.Lock()  # 新增：硬體通訊鎖
        if LOBOROBOT:
            try:
                self.robot = LOBOROBOT()
                print("LOBOROBOT 硬體驅動成功！")
            except Exception as e:
                print(f"LOBOROBOT 初始化失敗: {e}")
                self.robot = None
        else:
            print("找不到 LOBOROBOT2 模組")
            self.robot = None

    def forward(self, speed=50):
        with self.lock:  # 鎖住 I2C 匯流排
            if self.robot:
                try:
                    self.robot.moveforward(speed)
                except TypeError:
                    self.robot.moveforward(speed, 0)

    def backward(self, speed=50):
        with self.lock:
            if self.robot:
                try:
                    self.robot.movebackward(speed)
                except TypeError:
                    self.robot.movebackward(speed, 0)

    def left(self, speed=50):
        with self.lock:
            if self.robot:
                try:
                    self.robot.turnLeft(speed)
                except TypeError:
                    self.robot.turnLeft(speed, 0)

    def right(self, speed=50):
        with self.lock:
            if self.robot:
                try:
                    self.robot.turnRight(speed)
                except TypeError:
                    self.robot.turnRight(speed, 0)

    def stop(self):
        with self.lock:
            if self.robot:
                try:
                    self.robot.t_stop()
                except TypeError:
                    self.robot.t_stop(0)

    def set_camera_servo(self, channel, angle, t_time=0.1):
        with self.lock:
            if self.robot and hasattr(self.robot, 'set_servo_angle'):
                try:
                    angle = int(angle)
                    self.robot.set_servo_angle(channel, angle, t_time)
                except Exception as e:
                    print(f"Servo Error: {e}")
