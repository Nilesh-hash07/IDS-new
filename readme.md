# INTRUSION DETECTION SYSTEM - README

## Overview
This is a hybrid Intrusion Detection System that combines Machine Learning (Random Forest) with rule-based detection to identify network attacks in real-time. It captures live traffic using TShark (Wireshark CLI) and analyzes flows every 5 seconds.

---

## FILES IN THIS PROJECT

| File | Purpose |
|------|---------|
| train_model_class_weights.py | Train the ML model on your dataset |
| live_detector_hybrid_balanced.py | Main detection script (run this) |
| advanced_attack_tester.py | Generate test attacks to verify detection |
| models/ | Folder where trained models are saved |

---

## HOW TO USE

### Step 1: Install Requirements
pip install pandas numpy scikit-learn joblib imbalanced-learn


### Step 2: Install TShark (Wireshark CLI)
- Download from: https://www.wireshark.org/download.html
- During installation, make sure to check "Install TShark"
- Default path: C:\Program Files\Wireshark\tshark.exe

### Step 3: Train the Model on Your Data
python train_model_class_weights.py

- Place your CSV files in data/raw/
- The script will ask for the label column name (usually 'Label' or ' Label')
- Trained model will be saved in models/ folder

### Step 4: Start Live Detection
python live_detector_hybrid_balanced.py "Wi-Fi"

Replace "Wi-Fi" with your network interface (e.g., "Ethernet", "eth0")

### Step 5: Test with Attacks (Optional)
In another terminal:
python advanced_attack_tester.py

Choose option 1 to run all attack tests

### Step 6: Stop Detection
Press Ctrl+C to stop and see final statistics

---

## CODE EXPLANATION - live_detector_hybrid_balanced.py

### 1. Initialization (__init__ method)
- Loads the trained ML model, scaler, label encoder, and feature names from models/
- Sets up network interface and statistics counters
- Initializes 5-second summary variables

### 2. Feature Extraction (_extract_features)
- Takes a flow (collection of packets with same 5-tuple)
- Calculates CIC-IDS2017 features like:
  - flow_duration
  - total_fwd_packets
  - packet lengths (max, min, mean, std)
  - bytes per second
  - packets per second
  - inter-arrival times
  - flag counts (SYN, ACK)
  - port counts
- Returns a feature vector matching what the model expects

### 3. Rule-Based Detection (_rule_based_detection)
Contains 5 balanced rules with medium thresholds:

| Attack Type | Threshold | Confidence |
|------------|-----------|------------|
| Port Scan | >15 ports AND >5 pps | 85% |
| DDoS | >200 pps | 90% |
| Data Exfiltration | >2 MB/s | 85% |
| SSH Bruteforce | >15 packets AND >2 pps | 80% |
| SYN Flood | >50 SYNs AND >50 pps | 90% |

### 4. Hybrid Prediction (_predict_flow)
- Gets ML prediction and confidence
- Gets rule-based detection result
- Combines them with these rules:
  - Both agree → Attack (average confidence)
  - ML only with confidence >60% → Attack
  - Rules only with confidence >50% → Attack
- Updates statistics
- Generates alerts if attack detected

### 5. Packet Processing (_process_packets)
- Reads packets from TShark in real-time
- Groups packets into flows using 5-tuple (src_ip:src_port-dst_ip:dst_port-proto)
- When flow has enough packets (>=5) or age (>3 seconds), sends to _predict_flow

### 6. 5-Second Summary (_show_summary and _summary_loop)
- Every 5 seconds, displays:
  - Total packets in last 5 seconds
  - Flows analyzed
  - Alerts generated
  - Attack types detected
  - Recent alerts
- Resets counters after each summary

### 7. Main Loop
- Starts TShark capture thread
- Starts summary thread
- Waits for Ctrl+C to stop

### Key Features
- Balanced rules 
- Clean 5-second summaries
- Hybrid detection covers ML blindspots
