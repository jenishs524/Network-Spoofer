#!/usr/bin/env python3
"""
Ultimate Spoofer v6.0 - Full Anonymity
- Random MAC & local IP (same subnet)
- Random VPN server from different countries
- Rotates every interval, keeps internet alive
- Restores original settings on exit
"""

import subprocess, random, time, argparse, sys, signal, re, os, logging, glob
from typing import Optional, Tuple

# ---------- Configuration ----------
VPN_CONFIG_DIR = "/etc/openvpn/configs/"   # where your .ovpn files are stored
LOG_FILE = "/var/log/ultimate_spoofer.log"
INTERVAL = 5   # seconds between cycles

# ---------- Global state ----------
interface = None
original_mac = None
original_ip = None
gateway = None
prefix = None
vpn_process = None
running = True
nm_managed = False

logging.basicConfig(level=logging.INFO,
                    format="[%(asctime)s] %(levelname)s: %(message)s",
                    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()])
logger = logging.getLogger("UltimateSpoofer")

# ---------- Utility functions ----------
def run_cmd(cmd, check=False):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=check)
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {' '.join(cmd)} -> {e.stderr.strip()}")
        return e

def get_interface_info(iface):
    out = run_cmd(["ip", "a", "show", iface]).stdout
    mac = re.search(r"link/ether ([0-9a-f:]{17})", out)
    ip = re.search(r"inet (\d+\.\d+\.\d+\.\d+/\d+)", out)
    return (mac.group(1) if mac else None, ip.group(1) if ip else None)

def get_gateway_and_prefix(iface):
    route = run_cmd(["ip", "route", "show", "dev", iface]).stdout
    gw_match = re.search(r"default via (\d+\.\d+\.\d+\.\d+)", route)
    if not gw_match:
        logger.warning("No gateway found; falling back to /24.")
        return None, 24
    _, ip_with_mask = get_interface_info(iface)
    prefix = int(ip_with_mask.split('/')[1]) if ip_with_mask else 24
    return gw_match.group(1), prefix

def random_ip_in_subnet(gw, prefix):
    parts = list(map(int, gw.split('.')))
    host_bits = 32 - prefix
    max_hosts = (1 << host_bits) - 2
    if max_hosts < 1: prefix, host_bits = 24, 8; max_hosts = 254
    # Build network base
    net_parts = parts.copy()
    mask_bits = prefix
    for i in range(4):
        if mask_bits >= 8:
            net_parts[i] = parts[i] & 0xFF
            mask_bits -= 8
        elif mask_bits > 0:
            net_parts[i] = parts[i] & (0xFF << (8 - mask_bits))
            mask_bits = 0
        else:
            net_parts[i] = 0
    host_int = random.randint(1, max_hosts)
    ip_parts = net_parts.copy()
    for i in range(3, -1, -1):
        if host_bits > 0:
            bits = min(8, host_bits)
            mask = (1 << bits) - 1
            ip_parts[i] = (ip_parts[i] & ~mask) | (host_int & mask)
            host_int >>= bits
            host_bits -= bits
    return ".".join(str(p) for p in ip_parts)

def random_mac():
    mac = [0x02, random.randint(0,255), random.randint(0,255),
           random.randint(0,255), random.randint(0,255), random.randint(0,255)]
    mac[0] |= 0x02
    return ":".join(f"{b:02x}" for b in mac)

def change_mac(iface, new_mac):
    try:
        run_cmd(["ip", "link", "set", iface, "down"])
        run_cmd(["ip", "link", "set", iface, "address", new_mac])
        run_cmd(["ip", "link", "set", iface, "up"])
        return True
    except: return False

def change_ip(iface, new_ip, prefix):
    try:
        run_cmd(["ip", "link", "set", iface, "down"])
        run_cmd(["ip", "addr", "flush", "dev", iface])
        run_cmd(["ip", "addr", "add", f"{new_ip}/{prefix}", "dev", iface])
        run_cmd(["ip", "link", "set", iface, "up"])
        return True
    except: return False

def disable_dhcp_permanently(iface):
    global nm_managed
    for client in ["dhclient", "dhcpcd", "pump", "udhcpc"]:
        run_cmd(["pkill", "-f", f"{client}.*{iface}"])
    try:
        if run_cmd(["systemctl", "is-active", "NetworkManager"]).returncode == 0:
            conf = f"/etc/NetworkManager/conf.d/99-unmanaged-{iface}.conf"
            with open(conf, "w") as f:
                f.write(f"[keyfile]\nunmanaged-devices=interface-name:{iface}\n")
            run_cmd(["systemctl", "restart", "NetworkManager"])
            nm_managed = True
            logger.info(f"NetworkManager disabled for {iface}")
    except Exception as e:
        logger.warning(f"Could not disable NetworkManager: {e}")

def restore_networkmanager(iface):
    if nm_managed:
        conf = f"/etc/NetworkManager/conf.d/99-unmanaged-{iface}.conf"
        if os.path.exists(conf):
            os.remove(conf)
            run_cmd(["systemctl", "restart", "NetworkManager"])
            logger.info("NetworkManager re-enabled")

def restore_original(iface, mac, ip):
    logger.info("Restoring original settings...")
    if mac: change_mac(iface, mac)
    if ip:
        run_cmd(["ip", "link", "set", iface, "down"])
        run_cmd(["ip", "addr", "flush", "dev", iface])
        run_cmd(["ip", "addr", "add", ip, "dev", iface])
        run_cmd(["ip", "link", "set", iface, "up"])
        logger.info(f"Restored IP to {ip}")
    restore_networkmanager(iface)

# ---------- VPN control ----------
def get_vpn_configs():
    """Return list of .ovpn file paths."""
    return glob.glob(os.path.join(VPN_CONFIG_DIR, "*.ovpn"))

def start_vpn(config_file):
    """Start OpenVPN with given config, return process object."""
    global vpn_process
    if vpn_process and vpn_process.poll() is None:
        stop_vpn()
    logger.info(f"Starting VPN with config: {os.path.basename(config_file)}")
    # Use --daemon to run in background, but we want to control it
    # We'll run it with --writepid and --log for monitoring, but simpler: we'll use subprocess.Popen
    vpn_process = subprocess.Popen(["openvpn", "--config", config_file],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Wait a few seconds for connection
    time.sleep(5)
    # Check if tun interface appears (optional)
    return vpn_process

def stop_vpn():
    global vpn_process
    if vpn_process and vpn_process.poll() is None:
        logger.info("Stopping VPN...")
        vpn_process.terminate()
        try:
            vpn_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            vpn_process.kill()
        vpn_process = None

def get_public_ip():
    """Get current public IP (for logging)."""
    try:
        result = subprocess.run(["curl", "-s", "ifconfig.me"], capture_output=True, text=True, timeout=5)
        return result.stdout.strip()
    except:
        return "unknown"

# ---------- Signal handler ----------
def signal_handler(sig, frame):
    global running
    logger.info("Interrupt received. Restoring...")
    running = False
    stop_vpn()
    restore_original(interface, original_mac, original_ip)
    sys.exit(0)

# ---------- Main ----------
def main():
    global interface, original_mac, original_ip, gateway, prefix

    parser = argparse.ArgumentParser(description="Ultimate Spoofer with VPN rotation")
    parser.add_argument("-i", "--interface", required=True, help="Network interface (e.g., wlan0)")
    parser.add_argument("--interval", type=float, default=5.0, help="Rotation interval (seconds)")
    args = parser.parse_args()

    if os.geteuid() != 0:
        logger.error("Must be root.")
        sys.exit(1)

    interface = args.interface
    original_mac, original_ip = get_interface_info(interface)
    if not original_mac:
        logger.error(f"Interface {interface} not found.")
        sys.exit(1)

    gateway, prefix = get_gateway_and_prefix(interface)
    if not gateway:
        logger.error("Could not determine gateway. Aborting.")
        sys.exit(1)

    logger.info(f"Original MAC: {original_mac}")
    logger.info(f"Original IP : {original_ip}")
    logger.info(f"Gateway: {gateway}, Prefix: /{prefix}")

    # Disable DHCP
    disable_dhcp_permanently(interface)

    # Get available VPN configs
    configs = get_vpn_configs()
    if not configs:
        logger.error("No VPN config files found in " + VPN_CONFIG_DIR)
        sys.exit(1)
    logger.info(f"Found {len(configs)} VPN configs.")

    # Set signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    round_num = 0
    while running:
        # 1. Pick random VPN config
        vpn_conf = random.choice(configs)
        country = os.path.basename(vpn_conf).replace(".ovpn", "")
        logger.info(f"Round {round_num+1}: Connecting to VPN country: {country}")

        # 2. Start VPN (this changes public IP)
        start_vpn(vpn_conf)

        # 3. Change MAC and local IP
        new_mac = random_mac()
        new_ip = random_ip_in_subnet(gateway, prefix)
        ip_str = f"{new_ip}/{prefix}"
        logger.info(f"New MAC: {new_mac}, New local IP: {ip_str}")

        if change_mac(interface, new_mac):
            logger.info("MAC changed.")
        else:
            logger.error("MAC change failed.")

        if change_ip(interface, new_ip, prefix):
            logger.info("Local IP changed.")
        else:
            logger.error("Local IP change failed.")

        # 4. Log public IP (optional)
        pub_ip = get_public_ip()
        logger.info(f"Public IP now: {pub_ip} (country: {country})")

        round_num += 1
        time.sleep(args.interval)

    # Cleanup (though signal handler will do it)
    restore_original(interface, original_mac, original_ip)
    stop_vpn()

if __name__ == "__main__":
    main()