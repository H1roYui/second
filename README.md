# 🚗 AI Driver Academy - 樹莓派智慧自駕巡線小車

[![Python Version](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask-black.svg)](https://flask.palletsprojects.com/)
[![OpenCV](https://img.shields.io/badge/Vision-OpenCV%204.x-green.svg)](https://opencv.org/)
[![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi-red.svg)](https://www.raspberrypi.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

基於 **樹莓派 (Raspberry Pi)** 與 **Flask** 的開源智慧自駕車系統。本專案結合 **電腦視覺車道辨識 (OpenCV)**、**閉迴路控制 (PID Controller)**、**二軸視訊鏡頭雲台** 與 **Web 即時監控儀表板**，提供具備斷線急煞防護的高可靠性自主巡線小車。

---

## 📑 目錄

- [系統特色](#-系統特色)
- [系統架構](#-系統架構)
- [專案結構](#-專案結構)
- [硬體需求](#-硬體需求)
- [環境安裝與設定](#-環境安裝與設定)
- [快速啟動](#-快速啟動)
- [操作說明](#-操作說明)
- [核心演算法與控制](#-核心演算法與控制)
  - [1. 車道線影像處理](#1-車道線影像處理-lane_detectionpy)
  - [2. PID 自動轉向控制](#2-pid-自動轉向控制-pid_controllerpy)
  - [3. 通訊防斷線安全防護](#3-通訊防斷線安全防護-heartbeat-failsafe)
- [日誌記錄與分析](#-日誌記錄與分析)

---

## ✨ 系統特色

- **📷 雙色強健車道偵測**：
  - 支援黃線與白線的 HSV 動態閾值分割，具備自適應色彩容忍度。
  - 6 點多邊形自訂 ROI（感興趣區域）遮罩，排除車身與周圍天花板雜訊干擾。
  - 形態學開運算濾波 + Canny 邊緣偵測 + Hough 霍夫直線變換，過濾異常斜率雜線。
- **🤖 閉迴路 PID 自動循跡**：
  - 以車道中心偏移量（Offset）為誤差反饋，結合抗飽和積分（Anti-Windup）抑制超調。
  - 支援差速轉向控制，自動維持車輛行駛於車道正中央。
- **🌐 響應式 Web 監控儀表板**：
  - 低延遲 MJPEG 即時車載影像串流（顯示即時 FPS、處理延遲與濾除雜線數）。
  - 動態視覺化 Offset 指標條，即時反映小車離線程度。
  - 支援自駕/手動一鍵即時切換。
- **🎮 多元操控模式與鏡頭二軸雲台**：
  - 支援鍵盤快速鍵（`W` / `A` / `S` / `D` 車體移動、`方向鍵` 控制鏡頭二軸雲台角度）。
  - 支援行動裝置觸控/長按防誤觸機制。
- **🛡️ 斷線急煞安全機制 (Heartbeat Watchdog)**：
  - 後端維持心跳監聽，當網頁斷線或關閉超過 1.0 秒，立即觸發強制急煞停止。
- **📊 系統遙測記錄 (Telemetry Logging)**：
  - 背景每秒記錄車輛狀態（時間戳記、模式、連線、指令、Offset、轉向值與 CPU 溫度）至 CSV。

---

## 🏗️ 系統架構

```mermaid
flowchart TD
    subgraph Sensing["感知端 (Perception)"]
        Cam["Picamera2 (RGB 640x480)"] --> Frame["影像垂直翻轉 (BGR)"]
        Frame --> HSV["HSV 色彩過濾 (黃/白線)"]
        HSV --> ROI["6點 ROI 遮罩 + Canny"]
        ROI --> Hough["HoughLinesP + 斜率過濾"]
        Hough --> Offset["計算車道偏移量 (Offset)"]
    end

    subgraph Control["決策與控制 (Control)"]
        Offset --> PID["PID 控制器 (Kp/Ki/Kd)"]
        PID --> Steering["計算轉向修正值 (Steering)"]
        Heartbeat{"心跳檢測 (Heartbeat)"}
        Heartbeat -->|連線正常 & 自駕啟用| DriveAuto["驅動馬達循跡前進"]
        Heartbeat -->|> 1.0s 斷線| SafeStop["緊急煞車 (car.stop)"]
    end

    subgraph Hardware["硬體執行 (Actuation)"]
        DriveAuto --> LOBOROBOT["LOBOROBOT 驅動板 (I2C)"]
        ManualCmd["Web 手動操控 / 雲台舵機"] --> LOBOROBOT
    end

    subgraph Telemetry["遙測與監控 (Web UI)"]
        Steering --> Stream["MJPEG 串流 + 遙測數據"]
        Stream --> Dashboard["Flask Web 儀表板 (Port 5000)"]
        SafeStop --> Log["car_status_log.csv 記錄"]
        DriveAuto --> Log
    end
