"""
Device Detector Utility
Parse user-agent string dan ekstrak informasi device dari HTTP request.

Catatan:
- Tidak menggunakan library eksternal (zero dependencies)
- Geolocation tidak diimplementasikan secara default karena memerlukan
  layanan eksternal (MaxMind GeoLite2, ip-api.com, dst).
  Tambahkan implementasi di get_geolocation_from_ip() jika diperlukan.
"""
import re
from typing import Dict, Optional
from fastapi import Request


def get_client_ip(request: Request) -> str:
    """
    Ekstrak IP asli client dari request.
    Menangani header reverse proxy (Nginx, Cloudflare, AWS ELB).

    Prioritas:
      1. X-Forwarded-For  (header standar reverse proxy, ambil IP pertama)
      2. X-Real-IP        (header alternatif Nginx)
      3. request.client.host (koneksi langsung)

    Args:
        request: FastAPI Request object.

    Returns:
        IP address sebagai string, atau "unknown" jika tidak ditemukan.
    """
    # X-Forwarded-For: client, proxy1, proxy2 — ambil yang paling kiri
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    return request.client.host if request.client else "unknown"


def parse_user_agent(user_agent_string: str) -> Dict[str, Optional[str]]:
    """
    Parse user-agent string untuk mengekstrak browser, OS, device type, dan model.

    Args:
        user_agent_string: Nilai header User-Agent dari HTTP request.

    Returns:
        Dict dengan key: browser, os, device_type, device_model.
    """
    if not user_agent_string:
        return {"browser": None, "os": None, "device_type": "web", "device_model": None}

    ua = user_agent_string.lower()

    # ── Browser ──────────────────────────────────────────────────────────────
    browser: Optional[str] = None
    if "edg" in ua:
        browser = "Microsoft Edge"
        m = re.search(r"edg(?:e)?/([\d.]+)", ua)
    elif "opr" in ua or "opera" in ua:
        browser = "Opera"
        m = re.search(r"(?:opr|opera)/([\d.]+)", ua)
    elif "chrome" in ua and "safari" in ua:
        browser = "Google Chrome"
        m = re.search(r"chrome/([\d.]+)", ua)
    elif "firefox" in ua:
        browser = "Mozilla Firefox"
        m = re.search(r"firefox/([\d.]+)", ua)
    elif "safari" in ua:
        browser = "Safari"
        m = re.search(r"version/([\d.]+)", ua)
    elif "msie" in ua or "trident" in ua:
        browser = "Internet Explorer"
        m = re.search(r"(?:msie |rv:)([\d.]+)", ua)
    else:
        browser = "Unknown Browser"
        m = None

    if m and browser:
        browser = f"{browser} {m.group(1)}"

    # ── OS ───────────────────────────────────────────────────────────────────
    os: Optional[str] = None
    if "windows nt 10" in ua:
        os = "Windows 10/11"
    elif "windows nt 6.3" in ua:
        os = "Windows 8.1"
    elif "windows nt 6.2" in ua:
        os = "Windows 8"
    elif "windows nt 6.1" in ua:
        os = "Windows 7"
    elif "windows" in ua:
        os = "Windows"
    elif "mac os x" in ua or "macos" in ua:
        mv = re.search(r"mac os x ([\d_]+)", ua)
        os = f"macOS {mv.group(1).replace('_', '.')}" if mv else "macOS"
    elif "android" in ua:
        av = re.search(r"android ([\d.]+)", ua)
        os = f"Android {av.group(1)}" if av else "Android"
    elif "iphone" in ua or "ipad" in ua:
        iv = re.search(r"os ([\d_]+)", ua)
        os = f"iOS {iv.group(1).replace('_', '.')}" if iv else "iOS"
    elif "ubuntu" in ua:
        os = "Ubuntu"
    elif "linux" in ua:
        os = "Linux"
    else:
        os = "Unknown OS"

    # ── Device type & model ──────────────────────────────────────────────────
    device_type = "web"
    device_model: Optional[str] = None

    if "ipad" in ua or "tablet" in ua:
        device_type = "tablet"
    elif "mobile" in ua or "android" in ua or "iphone" in ua:
        device_type = "mobile"

    if device_type in ("mobile", "tablet"):
        if "android" in ua:
            mm = re.search(r";\s*([^;)]+)\s+build", ua)
            if mm:
                device_model = mm.group(1).strip().title()
        elif "iphone" in ua:
            device_model = "iPhone"
        elif "ipad" in ua:
            device_model = "iPad"

    return {
        "browser": browser,
        "os": os,
        "device_type": device_type,
        "device_model": device_model,
    }


def detect_device_info(request: Request) -> Dict[str, Optional[str]]:
    """
    Ekstrak seluruh informasi device dari HTTP request.

    Args:
        request: FastAPI Request object.

    Returns:
        Dict dengan key:
          - ip_address   : IP asli client
          - user_agent   : Full user-agent string
          - browser      : Browser dengan versi
          - os           : Sistem operasi
          - device_type  : "web" | "mobile" | "tablet"
          - device_model : Model device (hanya mobile/tablet)
    """
    ua_string = request.headers.get("user-agent", "")
    parsed = parse_user_agent(ua_string)
    return {
        "ip_address": get_client_ip(request),
        "user_agent": ua_string or None,
        **parsed,
    }
