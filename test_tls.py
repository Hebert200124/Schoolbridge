import ssl
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)

session = requests.Session()
session.mount('https://', TLSAdapter())

print("Testing with forced TLS 1.2...")
try:
    r = session.get("https://api.sandbox.africastalking.com", timeout=10)
    print("SUCCESS:", r.status_code)
except Exception as e:
    print("FAILED:", e)
