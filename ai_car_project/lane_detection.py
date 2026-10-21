# -*- coding: utf-8 -*-
import cv2
import numpy as np
import time

class LaneDetector:
    def __init__(self, width=640, height=480):
        self.width = width
        self.height = height
        self.prev_time = time.time()

    def process_frame(self, frame):
        start_time = time.time()
        h, w = frame.shape[:2]
        mid_x = w // 2

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 【放寬】黃線範圍：涵蓋更淺與更深的黃色
        lower_yellow = np.array([10, 40, 40])
        upper_yellow = np.array([45, 255, 255])
        mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
        
        # 【放寬】白線範圍：亮度下限大幅降至 100，飽和度容許至 60
        lower_white = np.array([0, 0, 100])
        upper_white = np.array([180, 60, 255])
        mask_white = cv2.inRange(hsv, lower_white, upper_white)
        
        color_mask = cv2.bitwise_or(mask_yellow, mask_white)

        # 形態學開運算 (保留去雜訊能力)
        kernel = np.ones((5, 5), np.uint8)
        color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_OPEN, kernel)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_masked = cv2.bitwise_and(gray, gray, mask=color_mask)
        
        blur = cv2.GaussianBlur(gray_masked, (5, 5), 0)
        edges = cv2.Canny(blur, 50, 150)

        # 6 點多邊形 ROI
        pts = np.array([
            [0.02 * w, 0.98 * h], 
            [0.10 * w, 0.65 * h], 
            [0.25 * w, 0.45 * h], 
            [0.75 * w, 0.45 * h], 
            [0.90 * w, 0.65 * h], 
            [0.98 * w, 0.98 * h]   
        ], dtype=np.int32)
        
        mask_roi = np.zeros_like(edges)
        cv2.fillPoly(mask_roi, [pts], 255)
        roi_edges = cv2.bitwise_and(edges, edges, mask=mask_roi)

        # Hough 直線檢測
        lines = cv2.HoughLinesP(roi_edges, 1, np.pi / 180, 30, minLineLength=25, maxLineGap=20)

        offset = 0.0
        overlay = frame.copy()
        
        cv2.polylines(overlay, [pts], isClosed=True, color=(255, 255, 0), thickness=2)
        cv2.line(overlay, (mid_x, int(h * 0.6)), (mid_x, h), (255, 0, 0), 1)

        left_points = []
        right_points = []
        false_lines_count = 0

        if lines is not None:
            for line in lines.reshape(-1, 4):
                x1, y1, x2, y2 = int(line[0]), int(line[1]), int(line[2]), int(line[3])
                if x2 == x1:
                    continue
                slope = (y2 - y1) / float(x2 - x1)
                
                # 【放寬】斜率過濾：容忍更平滑與更垂直的線條 (0.20 ~ 10.0)
                if abs(slope) < 0.20 or abs(slope) > 10.0:
                    false_lines_count += 1
                    continue

                if slope < 0 and x1 < mid_x and x2 < mid_x:
                    left_points.extend([(x1, y1), (x2, y2)])
                    cv2.line(overlay, (x1, y1), (x2, y2), (0, 255, 0), 2)
                elif slope > 0 and x1 > mid_x and x2 > mid_x:
                    right_points.extend([(x1, y1), (x2, y2)])
                    cv2.line(overlay, (x1, y1), (x2, y2), (0, 255, 0), 2)
                else:
                    false_lines_count += 1

            if len(left_points) > 0 and len(right_points) > 0:
                left_mean_x = np.mean([p[0] for p in left_points])
                right_mean_x = np.mean([p[0] for p in right_points])
                lane_center = (left_mean_x + right_mean_x) / 2.0
                offset = lane_center - mid_x

                cv2.circle(overlay, (int(lane_center), int(h * 0.8)), 6, (0, 0, 255), -1)
                cv2.line(overlay, (mid_x, int(h * 0.8)), (int(lane_center), int(h * 0.8)), (0, 0, 255), 2)
            
        process_latency = (time.time() - start_time) * 1000
        current_time = time.time()
        time_diff = current_time - self.prev_time
        fps = 1.0 / time_diff if time_diff > 0 else 0
        self.prev_time = current_time

        cv2.putText(overlay, f"False Lines Filtered: {false_lines_count}", (15, 35), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        cv2.putText(overlay, f"FPS: {int(fps)}", (15, 65), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(overlay, f"Latency: {int(process_latency)} ms", (15, 95), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        return overlay, offset
