# -*- coding: utf-8 -*-
import time

class PIDController:
    def __init__(self, Kp=0.35, Ki=0.005, Kd=0.08, setpoint=0.0):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.setpoint = setpoint  # 目標偏差量 (小車處於道路中央時為 0)
        self.prev_error = 0.0
        self.integral = 0.0
        self.last_time = time.time()

    def update(self, current_offset):
        current_time = time.time()
        dt = current_time - self.last_time
        if dt <= 0.0:
            dt = 1e-4

        error = self.setpoint - current_offset
        self.integral += error * dt
        # 積分限幅防止飽和
        self.integral = max(-50.0, min(50.0, self.integral))

        derivative = (error - self.prev_error) / dt
        output = (self.Kp * error) + (self.Ki * self.integral) + (self.Kd * derivative)

        self.prev_error = error
        self.last_time = current_time
        return output

    def reset(self):
        self.prev_error = 0.0
        self.integral = 0.0
        self.last_time = time.time()