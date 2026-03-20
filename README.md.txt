🛡️ IoT-Scanner v10.8
Automated IoT Reconnaissance & Vulnerability Framework
IoT-Scanner is a high-performance Python framework designed to audit local network environments for vulnerable IoT devices. It combines multi-threaded reconnaissance, hardware fingerprinting, and automated credential sniping to identify security gaps in common consumer and industrial hardware.

🚀 Key Features
Intelligence Discovery: Uses ThreadPoolExecutor for asynchronous, sub-60-second subnet sweeps to identify active hosts.

Protocol-Specific Auditing:

HTTP/S: Intelligent directory busting with Content-Length baseline filtering to find hidden /admin, /config, or /env portals.

SSH/Telnet: Vendor-aware credential sniping (mapping MAC addresses to hardware-specific default password databases).

FTP: Automated anonymous access verification and directory listing.

Evasion & Bypass: Includes an Aggressive AP-Bypass mode using static ARP injection to circumvent Access Point (AP) Isolation.

Hardware Fingerprinting: Leverages Nmap NSE (Nmap Scripting Engine) to identify vendors (Hikvision, Dahua, Cisco, TP-Link, etc.) and suggest specific attack vectors.

🛠️ Installation & Setup
1. Prerequisites
Ensure you have Nmap installed on your host system:

Bash
sudo apt update && sudo apt install nmap -y
2. Clone & Install Dependencies
Bash
git clone https://github.com/VARIYA4444/IoT-Scanner.git
cd IoT-Scanner
pip install -r requirements.txt
3. Requirements
The framework requires the following Python libraries (included in requirements.txt):

python-nmap

paramiko

requests

📖 Usage
The tool must be run with root privileges for ARP manipulation and raw socket access.

Bash
sudo python3 iot_scanner.py
Engagement Modes:
Standard Scan: Passive discovery and service auditing. Safe for production environments.

Aggressive AP-Bypass: Forcibly maps the gateway MAC to target IPs to bypass network-level client isolation (AP Isolation).

📊 Technical Workflow
Environment Mapping: Retrieves subnet CIDR and gateway configuration automatically.

Phase 1 (Discovery): Fast TCP-handshake sweep across common IoT ports (21, 22, 23, 80, 443, 554, 8080).

Phase 2 (Audit): Nmap-driven service versioning and script execution for deep fingerprinting.

Phase 3 (Exploitation): Targeted credential sniping based on hardware vendor identification.

⚠️ Legal Disclaimer
FOR EDUCATIONAL PURPOSES ONLY. Usage of IoT-Scanner for attacking targets without prior mutual consent is illegal. It is the end user's responsibility to obey all applicable local, state, and federal laws. Developers assume no liability and are not responsible for any misuse or damage caused by this program.

🎓 Academic Context
Developed as part of an MSc Advanced Computing security research portfolio. This project explores the intersection of automated network reconnaissance and hardware-specific vulnerability mapping.