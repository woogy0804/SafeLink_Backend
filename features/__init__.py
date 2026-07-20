from urllib.parse import urlparse
import socket
import ipaddress

def validate_url(url):
    parsed = urlparse(url)

    if parsed.scheme not in ("http","https"):
        raise ValueError("http/https only")

    if not parsed.hostname:
        raise ValueError("httpname required")

    return parsed.hostname

def block_private_ip(hostname):
    results = socket.getaddrinfo(hostname, None)

    for result in results:
        ip = result[4][0]
        ip_obj = ipaddress.ip_address(ip)

        if ip_obj.is_private or ip_obj.is_loopback:
            raise ValueError("private netword blocked")
