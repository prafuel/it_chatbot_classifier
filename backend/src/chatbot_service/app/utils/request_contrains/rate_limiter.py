
import os
import time
from dotenv import load_dotenv

from app.common.messages import LogMessages as Msg

load_dotenv()

LIMIT = int(os.getenv("LIMIT"))
COOLDOWN = int(os.getenv("COOLDOWN"))

ip_count = {}
ip_blocked_until = {}

def allow_request(ip):
    try:
        now = time.time()

        # if blocked → return remaining time
        if ip in ip_blocked_until:
            remaining = ip_blocked_until[ip] - now

            if remaining > 0:
                return False, round(remaining, 2)

            # cooldown finished → reset
            del ip_blocked_until[ip]
            ip_count[ip] = 0

        # increment counter
        ip_count[ip] = ip_count.get(ip, 0) + 1

        if ip_count[ip] > LIMIT:
            ip_blocked_until[ip] = now + COOLDOWN
            return False, COOLDOWN

        return True, 0
    except Exception as e:
        print(Msg.ALLOW_REQUEST_ERROR.format(e))
        return False, COOLDOWN