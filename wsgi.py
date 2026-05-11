# ── Force IPv4 before any imports that might open DB connections.
# Railway containers lack IPv6 routes; Supabase DNS often returns IPv6 first.
import socket

_orig_getaddrinfo = socket.getaddrinfo

def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    results = _orig_getaddrinfo(host, port, family, type, proto, flags)
    ipv4 = [r for r in results if r[0] == socket.AF_INET]
    return ipv4 if ipv4 else results

socket.getaddrinfo = _ipv4_only

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run()
