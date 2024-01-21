# Endpoints for Public API
import json


def login_url():
    return "https://public.com/userservice/public/web/login"


def mfa_url():
    return "https://public.com/userservice/public/web/verify-two-factor"


def refresh_url():
    return "https://public.com/userservice/public/web/token-refresh"


def portfolio_url(account_uuid):
    return f"https://prod-api.154310543964.hellopublic.com/hstier1service/account/{account_uuid}/portfolio"


def get_quote_url(symbol):
    return f"https://prod-api.154310543964.hellopublic.com/marketdataservice/stockcharts/last-trade/{symbol}"


def build_headers(auth=None):
    headers = {
        "authority": "public.com",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.5",
        "content-type": "application/json",
        "origin": "https://public.com",
        "referer": "https://public.com/login",
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Brave";v="120"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "sec-gpc": "1",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "x-app-version": "web-1.0.4",
    }
    if auth is not None:
        headers["authorization"] = auth
    return headers


def build_payload(email, password, code=None):
    payload = {
        "email": email,
        "password": password,
    }
    if code is None:
        payload["stayLoggedIn"] = True
    else:
        payload["verificationCode"] = code
    return json.dumps(payload)
