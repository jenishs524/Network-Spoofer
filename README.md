# Ultimate Network Spoofer – README

## 🚀 Project Overview

**Ultimate Network Spoofer** is a powerful anonymity tool that automatically rotates your **MAC address**, **local IP**, and **public IP (via VPN)** at regular intervals.  
It makes you virtually untraceable on your local network and from your ISP by constantly changing your identity.

This is an **expert‑level project** designed for privacy testing and educational purposes.  
Use it only on networks you own or have explicit permission to test.

---

## ✨ Features

- ✅ **Random MAC address** – changes your hardware identifier on the LAN.
- ✅ **Random local IP** – assigns a new IP within your subnet so internet stays up.
- ✅ **VPN rotation** – picks a random VPN server from a pool of countries, hiding your real public IP.
- ✅ **Automatic DHCP kill** – prevents automatic IP renewal from interfering with static IP changes.
- ✅ **Graceful restoration** – on exit (Ctrl+C), everything is restored to original settings (MAC, IP, VPN disconnect, NetworkManager re‑enabled).
- ✅ **Full logging** – logs all actions to `/var/log/ultimate_spoofer.log` and the terminal.

---

## 📦 Requirements

- **Operating System**: Linux (Debian‑based, tested on Kali).
- **Root privileges** – the script must run with `sudo`.
- **OpenVPN** – to connect to VPN servers.
- **VPN configuration files** (`.ovpn`) – one per country you want to appear from.
- **NetworkManager** – used to manage Wi‑Fi; the script temporarily disables it for the chosen interface.

---

## 🔧 Installation

### 1. Download the script

Place the script (`ultimate_spoofer.py`) in your preferred directory and make it executable:

```bash
chmod +x ultimate_spoofer.py
```

### 2. Install OpenVPN

```bash
sudo apt update
sudo apt install openvpn -y
```

### 3. Prepare VPN configuration files

Create a directory for your `.ovpn` files:

```bash
sudo mkdir -p /etc/openvpn/configs
```

Place your VPN configs (e.g., `US.ovpn`, `DE.ovpn`, `JP.ovpn`) inside that folder.  
You can get free configs from:

- [VPNBook](https://www.vpnbook.com/free-openvpn-account) – no registration required.
- [ProtonVPN](https://protonvpn.com/support/openvpn-config-files/) – requires a free account.

---

### 4. Configure VPN credentials (for VPNBook)

If you use VPNBook, run these commands to set up credentials automatically:

```bash
cd /etc/openvpn/configs
for file in *.ovpn; do
    echo "auth-user-pass /etc/openvpn/auth.txt" >> "$file"
done
echo -e "vpnbook\nHE2Rr3nD" | sudo tee /etc/openvpn/auth.txt
sudo chmod 600 /etc/openvpn/auth.txt
```

> **Note**: The password (`HE2Rr3nD`) changes occasionally – check [VPNBook](https://www.vpnbook.com/free-openvpn-account) for the latest one.

---

## 🛠 Usage

Run the script with `sudo`:

```bash
sudo ./ultimate_spoofer.py -i wlan0 --interval 10
```

- `-i wlan0` – replace with your network interface (e.g., `eth0`, `wlan0`).  
- `--interval 10` – time in seconds between each identity rotation (default 5).

---

### Example Output

```
[2026-09-09 03:23:45,446] INFO: Original MAC: 9c:b6:d0:19:55:07
[2026-09-09 03:23:45,446] INFO: Original IP : 192.168.18.219/24
[2026-09-09 03:23:45,446] INFO: Gateway: 192.168.18.1, Prefix: /24
[2026-09-09 03:23:45,446] INFO: Found 5 VPN configs.
[2026-09-09 03:23:45,446] INFO: Round 1: Connecting to VPN country: US
[2026-09-09 03:23:45,446] INFO: New MAC: 02:ed:54:52:3d:a4, New local IP: 192.168.18.45/24
[2026-09-09 03:23:45,446] INFO: MAC changed.
[2026-09-09 03:23:45,446] INFO: Local IP changed.
[2026-09-09 03:23:45,446] INFO: Public IP now: 45.33.22.11 (country: US)
```

---

## 🔄 How It Works

1. **Disables DHCP** – kills `dhclient`, `dhcpcd`, and tells NetworkManager to stop managing the interface (creates `/etc/NetworkManager/conf.d/99-unmanaged-*.conf`).
2. **Chooses a random VPN config** – picks a `.ovpn` file from the config directory.
3. **Starts OpenVPN** – connects to the chosen server; your public IP changes.
4. **Generates a random MAC** – ensures the second bit of the first byte is set to `1` (locally administered).
5. **Generates a random local IP** – within the same subnet as your gateway, so your route to the internet remains functional.
6. **Applies changes** – flushes old IP, assigns new IP, updates MAC.
7. **Waits** for the interval, then repeats from step 2.
8. **On Ctrl+C** – restores original MAC and IP, disconnects VPN, re‑enables NetworkManager.

---

## 🧪 Troubleshooting

### Wi‑Fi disappears after running the script

The script disables NetworkManager to prevent DHCP interference.  
If the script crashes or you forget to stop it with `Ctrl+C`, run:

```bash
sudo rm -f /etc/NetworkManager/conf.d/99-unmanaged-*.conf
sudo service NetworkManager restart
sudo nmcli device set wlan0 managed yes
sudo nmcli radio wifi on
sudo ip link set wlan0 up
```

*(Replace `wlan0` with your interface.)*

### `systemctl: command not found`

Your PATH may be broken. Use `service` instead:

```bash
sudo service NetworkManager restart
```

Or fix your PATH:

```bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

### No VPN configs found

Place your `.ovpn` files in `/etc/openvpn/configs/` and ensure they have the correct permissions (`chmod 644`).

### Internet drops after IP change

The script only changes your local IP, not the gateway or DNS.  
If you lose connectivity, ensure the new IP is in the same subnet as your gateway.  
The script does this automatically, but if your gateway changes, you may need to update it.

### VPN connection fails

Check the credentials in `/etc/openvpn/auth.txt`.  
For VPNBook, ensure the password is up‑to‑date.  
Also, ensure OpenVPN is installed and your firewall allows VPN traffic.

---

## 🛡️ Security & Anonymity Notes

- This tool **does not** make you completely anonymous – it only changes local identifiers and routes traffic through a VPN.
- Your ISP can still see that you are using a VPN, but cannot see the contents of your traffic (encrypted).
- To achieve maximum anonymity, combine this with **Tor** and **private browsing** habits.
- Always use **trusted VPN providers** that keep no logs.

---

## 📁 File Structure

```
ultimate_spoofer.py          # Main script
/etc/openvpn/configs/        # Directory for .ovpn files
  ├── US.ovpn
  ├── DE.ovpn
  └── JP.ovpn
/etc/openvpn/auth.txt        # VPN credentials (for VPNBook)
/var/log/ultimate_spoofer.log # Log file
```

---

## 🧑‍💻 Author & License

- **Author**: Jenishkali (anonymity enthusiast)
- **License**: MIT – use at your own risk.
- **Disclaimer**: This tool is for **educational and authorised testing purposes only**. Misuse on networks without permission is illegal.

---

## 📄 Script Source

The script is available in the repository. Save it as `ultimate_spoofer.py` and follow the installation steps above.

---

## 🎯 Next Steps

1. **Test the script** with a few VPN configs first.
2. **Monitor** your IP changes with `watch -n 1 curl ifconfig.me`.
3. **Adjust the interval** to balance speed and stability.
4. **Expand** your VPN pool by adding more country configs.

---

Happy spoofing – and stay private! 🔒