# live_detector_hybrid_balanced.py
"""
LIVE DETECTION - ML + Rule-Based Hybrid
- Balanced rules (medium strictness)
- Combined 5-second summaries
- No emojis
"""

import subprocess
import pandas as pd
import numpy as np
import joblib
import threading
import time
import json
import os
import warnings
from datetime import datetime
from collections import defaultdict

warnings.filterwarnings("ignore")

class LiveIDS:
    def __init__(self, interface='Wi-Fi'):
        print("=" * 70)
        print("LIVE IDS - HYBRID DETECTION (Balanced Rules)")
        print("=" * 70)
        
        # Load model
        model_path = "models/ids_model_class_weights.pkl"
        encoder_path = "models/label_encoder_class_weights.pkl"
        features_path = "models/feature_names_class_weights.pkl"
        scaler_path = "models/scaler_class_weights.pkl"
        
        if not os.path.exists(model_path):
            print(f"\nModel not found at: {model_path}")
            print("Please run train_model_class_weights.py first!")
            exit(1)
        
        # Load model
        print(f"\nLoading ML model...")
        self.model = joblib.load(model_path)
        print(f"  Model loaded")
        
        # Load scaler
        self.scaler = joblib.load(scaler_path)
        print(f"  Scaler loaded")
        
        # Load label encoder
        self.label_encoder = joblib.load(encoder_path)
        self.attack_types = self.label_encoder.classes_
        print(f"  ML model can detect {len(self.attack_types)} attack types")
        
        # Load feature names
        self.feature_names = joblib.load(features_path)
        print(f"  Model expects {len(self.feature_names)} features")
        
        # Settings
        self.interface = interface
        self.running = False
        self.tshark_process = None
        self.alerts = []
        self.flows = {}
        
        # Statistics
        self.stats = {
            'total_packets': 0,
            'total_flows': 0,
            'flows_analyzed': 0,
            'attacks_detected': 0,
            'benign_flows': 0,
            'total_alerts': 0,
            'attacks_by_type': defaultdict(int)
        }
        
        # For 5-second summaries
        self.last_summary_time = time.time()
        self.summary_packets = 0
        self.summary_flows = 0
        self.summary_alerts = 0
        self.summary_attacks = defaultdict(int)
        
        # Find TShark
        self.tshark_path = self._find_tshark()
        if not self.tshark_path:
            print("\nTShark not found!")
            exit(1)
        
        print(f"\nInterface: {interface}")
        print(f"TShark: {self.tshark_path}")
        print("\n" + "=" * 70)
        print("HYBRID DETECTION ACTIVE:")
        print("  • Balanced rules (medium strictness)")
        print("  • Combined 5-second summaries")
        print("  • Press Ctrl+C to stop")
        print("=" * 70)
    
    def _find_tshark(self):
        paths = [
            r"C:\Program Files\Wireshark\tshark.exe",
            r"C:\Program Files (x86)\Wireshark\tshark.exe",
        ]
        for path in paths:
            if os.path.exists(path):
                return path
        return None
    
    def _extract_features(self, flow):
        """Extract features from flow for ML model"""
        
        if len(flow['timestamps']) < 2:
            return None
        
        timestamps = np.array(flow['timestamps'])
        bytes_arr = np.array(flow['bytes'])
        
        duration = timestamps[-1] - timestamps[0]
        if duration <= 0:
            duration = 0.001
        
        total_packets = len(flow['packets'])
        total_bytes = np.sum(bytes_arr)
        
        # Calculate features
        calculated = {
            'flow_duration': duration,
            'total_fwd_packets': total_packets,
            'total_length_fwd_packets': total_bytes,
            'fwd_packet_length_max': np.max(bytes_arr) if len(bytes_arr) > 0 else 0,
            'fwd_packet_length_min': np.min(bytes_arr) if len(bytes_arr) > 0 else 0,
            'fwd_packet_length_mean': np.mean(bytes_arr) if len(bytes_arr) > 0 else 0,
            'fwd_packet_length_std': np.std(bytes_arr) if len(bytes_arr) > 1 else 0,
            'flow_bytes_per_sec': total_bytes / duration,
            'flow_packets_per_sec': total_packets / duration,
        }
        
        # Inter-arrival times
        if len(timestamps) > 1:
            iat = np.diff(timestamps)
            calculated['flow_iat_mean'] = np.mean(iat)
            calculated['flow_iat_std'] = np.std(iat)
            calculated['flow_iat_max'] = np.max(iat)
            calculated['flow_iat_min'] = np.min(iat)
        
        # Flag features
        if flow['flags']:
            flags_str = ''.join(flow['flags'])
            calculated['syn_flag_count'] = flags_str.count('2')
            calculated['ack_flag_count'] = flags_str.count('16')
        
        # Port features
        calculated['src_port_count'] = len(flow['src_ports'])
        calculated['dst_port_count'] = len(flow['dst_ports'])
        
        # Create feature vector
        features = {}
        for name in self.feature_names:
            if name in calculated:
                features[name] = calculated[name]
            else:
                features[name] = 0
        
        return features
    
    def _rule_based_detection(self, flow):
        """
        BALANCED rule-based detection (medium thresholds)
        Returns: (is_attack, attack_type, confidence)
        """
        packets = len(flow['packets'])
        duration = flow['last_seen'] - flow['first_seen']
        if duration <= 0:
            duration = 0.001
        
        bytes_total = sum(flow['bytes'])
        packets_per_sec = packets / duration
        bytes_per_sec = bytes_total / duration
        unique_dst_ports = len(flow['dst_ports'])
        
        # ============================================
        # RULE 1: Port Scan Detection (BALANCED)
        # ============================================
        # Detect if scanning many ports
        if unique_dst_ports > 15 and packets_per_sec > 5:
            confidence = min(0.85, unique_dst_ports / 100)
            return True, "PortScan", confidence
        
        # ============================================
        # RULE 2: DDoS / Flood Detection (BALANCED)
        # ============================================
        # High packet rate
        if packets_per_sec > 200:
            confidence = min(0.9, packets_per_sec / 500)
            return True, "DDoS", confidence
        
        # ============================================
        # RULE 3: Data Exfiltration (BALANCED)
        # ============================================
        # High bandwidth transfer
        if bytes_per_sec > 2_000_000:  # > 2 MB/s
            confidence = 0.85
            return True, "DataExfiltration", confidence
        
        # ============================================
        # RULE 4: SSH Brute Force (BALANCED)
        # ============================================
        # Check if it's SSH traffic (port 22) with many packets
        if any('22' in str(port) for port in flow['dst_ports']):
            if packets > 15 and packets_per_sec > 2:
                confidence = min(0.8, packets / 50)
                return True, "SSH-Bruteforce", confidence
        
        # ============================================
        # RULE 5: SYN Flood (BALANCED)
        # ============================================
        if flow['flags']:
            flags_str = ''.join(flow['flags'])
            syn_count = flags_str.count('2')
            if syn_count > 50 and packets_per_sec > 50:
                confidence = min(0.9, syn_count / 200)
                return True, "SYNFlood", confidence
        
        # No rule triggered
        return False, "BENIGN", 0.0
    
    def _predict_flow(self, flow, flow_id):
        """Hybrid prediction: ML + Rules (source hidden)"""
        
        # Extract features for ML
        features_dict = self._extract_features(flow)
        if not features_dict:
            return False
        
        # Create DataFrame for ML
        X = pd.DataFrame([features_dict])
        X = X[self.feature_names]
        
        packets = len(flow['packets'])
        duration = flow['last_seen'] - flow['first_seen']
        bytes_total = sum(flow['bytes'])
        
        try:
            # ========================================
            # STEP 1: ML MODEL PREDICTION
            # ========================================
            X_scaled = self.scaler.transform(X)
            
            ml_prediction = self.model.predict(X_scaled)[0]
            ml_probabilities = self.model.predict_proba(X_scaled)[0]
            ml_confidence = ml_probabilities[ml_prediction]
            
            ml_label = self.label_encoder.inverse_transform([ml_prediction])[0]
            
            # ========================================
            # STEP 2: RULE-BASED DETECTION
            # ========================================
            rule_detected, rule_attack, rule_confidence = self._rule_based_detection(flow)
            
            # ========================================
            # STEP 3: HYBRID DECISION (source hidden)
            # ========================================
            is_attack = False
            final_attack = "BENIGN"
            final_confidence = 0.0
            
            # Case 1: Both ML and Rules agree on attack
            if rule_detected and ml_label != 'BENIGN':
                is_attack = True
                final_attack = rule_attack
                final_confidence = (ml_confidence + rule_confidence) / 2
            
            # Case 2: Only ML detected attack (with decent confidence)
            elif ml_label != 'BENIGN' and ml_confidence > 0.6:
                is_attack = True
                final_attack = ml_label
                final_confidence = ml_confidence
            
            # Case 3: Only Rules detected attack
            elif rule_detected and rule_confidence > 0.5:
                is_attack = True
                final_attack = rule_attack
                final_confidence = rule_confidence
            
            # Update stats
            self.stats['flows_analyzed'] += 1
            self.summary_flows += 1
            self.summary_packets += packets
            
            # Generate alert if attack detected
            if is_attack:
                self.stats['attacks_detected'] += 1
                self.stats['total_alerts'] += 1
                self.stats['attacks_by_type'][final_attack] += 1
                self.summary_alerts += 1
                self.summary_attacks[final_attack] += 1
                
                # Severity based on confidence
                if final_confidence >= 0.8:
                    severity = "CRITICAL"
                elif final_confidence >= 0.6:
                    severity = "HIGH"
                elif final_confidence >= 0.4:
                    severity = "MEDIUM"
                else:
                    severity = "LOW"
                
                alert = {
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'attack_type': final_attack,
                    'severity': severity,
                    'confidence': f"{final_confidence:.1%}",
                    'packets': packets,
                    'bytes': bytes_total,
                    'pps': f"{packets/duration:.1f}",
                }
                self.alerts.append(alert)
                
                # Print alert immediately
                print(f"\nALERT! [{alert['timestamp']}] {severity}: {final_attack} ({alert['confidence']})")
            
            return is_attack
            
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def _show_summary(self):
        """Show combined 5-second summary"""
        
        if self.summary_packets == 0 and self.summary_alerts == 0:
            return
        
        print("\n" + "=" * 70)
        print(f"5-SECOND SUMMARY - {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 70)
        print(f"Packets: {self.summary_packets}")
        print(f"Flows analyzed: {self.summary_flows}")
        print(f"Alerts: {self.summary_alerts}")
        
        if self.summary_attacks:
            print(f"\nAttacks detected:")
            for attack, count in self.summary_attacks.items():
                print(f"  • {attack}: {count}")
        
        # Show recent alerts (max 3)
        if self.alerts:
            print(f"\nRecent alerts:")
            for alert in self.alerts[-3:]:
                print(f"  • [{alert['timestamp']}] {alert['severity']}: {alert['attack_type']} ({alert['confidence']})")
        
        print("=" * 70)
        
        # Reset summary counters
        self.summary_packets = 0
        self.summary_flows = 0
        self.summary_alerts = 0
        self.summary_attacks.clear()
    
    def start(self):
        """Start capture"""
        self.running = True
        
        print("\nStarting TShark capture...")
        
        cmd = [
            self.tshark_path,
            '-i', self.interface,
            '-T', 'fields',
            '-e', 'frame.time_epoch',
            '-e', 'ip.src',
            '-e', 'ip.dst',
            '-e', 'ip.proto',
            '-e', 'tcp.srcport',
            '-e', 'tcp.dstport',
            '-e', 'udp.srcport',
            '-e', 'udp.dstport',
            '-e', 'frame.len',
            '-e', 'tcp.flags',
            '-E', 'header=n',
            '-E', 'separator=,'
        ]
        
        self.tshark_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        print("TShark started")
        print("\nHYBRID IDS RUNNING - Summary every 5 seconds")
        print("=" * 70)
        
        self.process_thread = threading.Thread(target=self._process_packets)
        self.process_thread.daemon = True
        self.process_thread.start()
        
        # Start summary thread
        self.summary_thread = threading.Thread(target=self._summary_loop)
        self.summary_thread.daemon = True
        self.summary_thread.start()
    
    def _summary_loop(self):
        """Show summary every 5 seconds"""
        while self.running:
            time.sleep(5)
            self._show_summary()
    
    def _process_packets(self):
        """Process packets"""
        flows = {}
        
        while self.running:
            try:
                line = self.tshark_process.stdout.readline()
                if not line:
                    continue
                
                self.stats['total_packets'] += 1
                
                # Parse packet
                parts = line.strip().split(',')
                if len(parts) < 8:
                    continue
                
                timestamp = float(parts[0]) if parts[0] else time.time()
                src_ip = parts[1] if parts[1] else '0.0.0.0'
                dst_ip = parts[2] if parts[2] else '0.0.0.0'
                proto = parts[3] if parts[3] else '0'
                src_port = parts[4] or parts[6] or '0'
                dst_port = parts[5] or parts[7] or '0'
                length = int(parts[8]) if len(parts) > 8 and parts[8] else 0
                tcp_flags = parts[9] if len(parts) > 9 and parts[9] else ''
                
                flow_id = f"{src_ip}:{src_port}-{dst_ip}:{dst_port}-{proto}"
                
                if flow_id not in flows:
                    flows[flow_id] = {
                        'packets': [], 'bytes': [], 'timestamps': [],
                        'src_ports': set(), 'dst_ports': set(), 'flags': [],
                        'first_seen': timestamp, 'last_seen': timestamp
                    }
                    self.stats['total_flows'] += 1
                
                flow = flows[flow_id]
                flow['packets'].append(1)
                flow['bytes'].append(length)
                flow['timestamps'].append(timestamp)
                flow['last_seen'] = timestamp
                flow['src_ports'].add(src_port)
                flow['dst_ports'].add(dst_port)
                if tcp_flags:
                    flow['flags'].append(tcp_flags)
                
                # Analyze after enough packets
                if len(flow['packets']) >= 5 or (timestamp - flow['first_seen']) > 3:
                    self._predict_flow(flow, flow_id)
                    del flows[flow_id]
                
            except Exception:
                continue
    
    def stop(self):
        """Stop capture"""
        self.running = False
        if self.tshark_process:
            self.tshark_process.terminate()
        
        # Show final summary
        self._show_summary()
        
        print("\n\n" + "=" * 70)
        print("FINAL STATISTICS")
        print("=" * 70)
        print(f"Total packets: {self.stats['total_packets']}")
        print(f"Total flows: {self.stats['total_flows']}")
        print(f"Flows analyzed: {self.stats['flows_analyzed']}")
        
        if self.stats['attacks_by_type']:
            print(f"\nAttacks detected:")
            for attack, count in self.stats['attacks_by_type'].items():
                print(f"  • {attack}: {count}")
        
        print(f"\nTotal alerts: {self.stats['total_alerts']}")
        print("=" * 70)


if __name__ == "__main__":
    import sys
    interface = sys.argv[1] if len(sys.argv) > 1 else 'Wi-Fi'
    
    ids = LiveIDS(interface=interface)
    
    try:
        ids.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        ids.stop()