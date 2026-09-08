# 🛡️ Network Spoofer

**Advanced Network Identity Rotator – MAC, IP & VPN Spoofing**

![Kali](https://img.shields.io/badge/OS-Kali_Linux-blue?logo=kalilinux)
![Python](https://img.shields.io/badge/Python-3.x-green?logo=python)
![OpenVPN](https://img.shields.io/badge/VPN-OpenVPN-orange?logo=openvpn)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## 📖 Table of Contents
- [Features](#features)
- [How It Works](#how-it-works)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Workflow](#workflow)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Security & Anonymity](#security--anonymity)
- [File Structure](#file-structure)
- [Contributing](#contributing)
- [License](#license)
- [Disclaimer](#disclaimer)

---

## 🌟 Features

- **Real MAC address randomisation** – changes your hardware identifier on the local network.
- **Real local IP randomisation** – assigns a new static IP within your subnet, keeping internet connectivity alive.
- **VPN country rotation** – connects to a random VPN server from a pool of countries, masking your real public IP.
- **Automatic DHCP suppression** – kills `dhclient`, `dhcpcd`, and disables NetworkManager for the interface to prevent IP renewal.
- **Graceful restoration** – on exit (Ctrl+C), restores original MAC, original IP, disconnects VPN, and re‑enables NetworkManager.
- **Comprehensive logging** – logs all actions to `/var/log/network_spoofer.log` and the terminal.
- **Fully automated** – no manual intervention after starting; runs in a loop with a configurable interval.

---

## ⚙️ How It Works

1. **Initialisation** – saves original MAC and IP; detects gateway and subnet mask.
2. **DHCP disable** – kills all DHCP clients and marks the interface as unmanaged for NetworkManager.
3. **Random selection** – picks a random `.ovpn` config file from the configured directory.
4. **VPN connection** – launches OpenVPN with that config (your public IP changes to the VPN server’s country).
5. **Random MAC generation** – creates a locally‑administered MAC (second bit of first byte set to `1`).
6. **Random local IP generation** – generates an IP within the same subnet as the gateway so routing remains intact.
7. **Apply changes** – flushes old IP, assigns new IP, updates MAC.
8. **Wait** – sleeps for the specified interval.
9. **Loop** – repeats from step 3.
10. **On interrupt (Ctrl+C)** – stops VPN, restores original MAC/IP, re‑enables NetworkManager.

---

## 📦 Requirements

- **Operating System**: Linux (Debian‑based, e.g., Kali, Ubuntu)
- **Root privileges** – the script must run with `sudo`.
- **OpenVPN** – installed (`sudo apt install openvpn`).
- **VPN configuration files** (`.ovpn`) – one per country.
- **NetworkManager** – optional but recommended (the script will temporarily disable it for the interface).
- **Python 3.6+** – with standard library modules (`subprocess`, `random`, `time`, `argparse`, `signal`, `re`, `os`, `logging`, `glob`).

---

## 🔧 Installation

### 1. Clone or Download the Script

Place the script (`network_spoofer.py`) in your preferred directory, e.g., `~/tools/network_spoofer/`.

Make it executable:
```bash
chmod +x network_spoofer.py
```

### 2. Install OpenVPN
```bash
sudo apt update
sudo apt install openvpn -y
```

### 3. Create VPN Config Directory
```bash
sudo mkdir -p /etc/openvpn/configs
```

### 4. Add VPN Configuration Files
Place your `.ovpn` files (e.g., `US.ovpn`, `DE.ovpn`, `JP.ovpn`) in `/etc/openvpn/configs/`.

You can obtain free configs from:
- [VPNBook](https://www.vpnbook.com/free-openvpn-account) (no registration)
- [ProtonVPN](https://protonvpn.com/support/openvpn-config-files/) (free account required)

### 5. (Optional) Configure Credentials for VPNBook
If using VPNBook, run these commands to embed credentials automatically:
```bash
cd /etc/openvpn/configs
for file in *.ovpn; do
    echo "auth-user-pass /etc/openvpn/auth.txt" >> "$file"
done
echo -e "vpnbook\nHE2Rr3nD" | sudo tee /etc/openvpn/auth.txt
sudo chmod 600 /etc/openvpn/auth.txt
```
> **Note:** The password `HE2Rr3nD` may change – check [VPNBook](https://www.vpnbook.com/free-openvpn-account) for the latest.

---

## 🚀 Usage

Run the script with root privileges:
```bash
sudo ./network_spoofer.py -i wlan0 --interval 10
```

**Arguments:**
| Option | Description | Default |
|--------|-------------|---------|
| `-i, --interface` | Network interface (e.g., `wlan0`, `eth0`) | **Required** |
| `--interval` | Time in seconds between each rotation | `5` |

**Example:**
```bash
sudo ./network_spoofer.py -i wlan0 --interval 15
```

While running, you can monitor changes in another terminal:
```bash
watch -n 1 ip a show wlan0
```
And check your public IP:
```bash
watch -n 1 curl -s ifconfig.me
```

To stop the script, press `Ctrl+C` – it will automatically restore everything.

---

## 🔄 Workflow

```
Start Script
    │
    ▼
Save original MAC & IP
    │
    ▼
Disable DHCP (kill dhclient, dhcpcd, mark unmanaged)
    │
    ▼
Loop forever:
    │
    ├─► Pick random VPN config
    ├─► Start OpenVPN (new public IP)
    ├─► Generate random MAC
    ├─► Generate random local IP in same subnet
    ├─► Apply MAC and IP changes
    ├─► Log changes
    ├─► Wait for interval
    └─► Repeat
    │
    ▼
Ctrl+C → Restore original MAC/IP, stop VPN, re‑enable NetworkManager
    │
    ▼
Exit
```

---

## ⚙️ Configuration

- **VPN config directory**: `/etc/openvpn/configs/` (change the `VPN_CONFIG_DIR` variable in the script if needed).
- **Log file**: `/var/log/network_spoofer.log` – all actions are logged here.
- **Unmanaged config**: The script creates `/etc/NetworkManager/conf.d/99-unmanaged-<interface>.conf` while running and removes it on exit.

---

## 🧪 Troubleshooting

### Wi‑Fi disappears after running the script
If the script crashes or you kill it abruptly, NetworkManager may still think the interface is unmanaged. Fix it with:
```bash
sudo rm -f /etc/NetworkManager/conf.d/99-unmanaged-*.conf
sudo service NetworkManager restart
sudo nmcli device set wlan0 managed yes
sudo nmcli radio wifi on
sudo ip link set wlan0 up
```
*(Replace `wlan0` with your interface.)*

### `systemctl: command not found`
If your system doesn’t have `systemctl`, use `service` instead:
```bash
sudo service NetworkManager restart
```
Or fix your PATH:
```bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

### No VPN configs found
Ensure your `.ovpn` files are in `/etc/openvpn/configs/` and have read permissions (`chmod 644`).

### VPN connection fails
- Check credentials in `/etc/openvpn/auth.txt`.
- Verify that OpenVPN is installed and your firewall allows UDP/TCP on the required ports.
- Test a config manually: `sudo openvpn --config /etc/openvpn/configs/US.ovpn`

### Internet drops after IP change
- The script always uses the same gateway and subnet, so connectivity should remain.
- If you lose connectivity, check if the gateway has changed (e.g., after reconnecting to Wi‑Fi). You may need to restart the script.

---

## 🛡️ Security & Anonymity

- This tool **only changes local identifiers** (MAC, local IP) and routes your traffic through a VPN.
- Your **ISP can still see** that you are using a VPN, but cannot inspect the encrypted traffic.
- The VPN provider sees the destination of your traffic; choose a **no‑log** provider for better privacy.
- For maximum anonymity, combine this with **Tor** and use **private browsing** modes.
- **Always test on networks you own or have permission to test.** Unauthorised spoofing may be illegal.

---

## 📁 File Structure

```
network_spoofer.py          # Main script
/etc/openvpn/configs/       # VPN .ovpn files
  ├── US.ovpn
  ├── DE.ovpn
  ├── JP.ovpn
  └── ...
/etc/openvpn/auth.txt       # VPN credentials (if using VPNBook)
/var/log/network_spoofer.log # Log file
```

---

## 🤝 Contributing

Contributions are welcome! If you find a bug or want to add features:
- Fork the repository
- Create a new branch
- Make your changes
- Submit a pull request with a clear description

---

## 📄 License

This project is licensed under the **MIT License** – see the [LICENSE](LICENSE) file for details.

---

## ⚠️ Disclaimer

**This tool is intended for educational and authorised testing purposes only.**  
Unauthorised use on networks without explicit permission is illegal and unethical. The authors assume no liability for any misuse or damage caused by this software. Use at your own risk.

---

**Happy spoofing – stay anonymous and safe!** 🛡️