# Endpoints for Public API
import json


class Endpoints:
    def __init__(self):
        self.baseurl = "https://public.com"
        self.prodapi = "https://prod-api.154310543964.hellopublic.com"
        self.ordergateway = f"{self.prodapi}/customerordergateway"
        self.userservice = f"{self.baseurl}/userservice"

    def login_url(self):
        return f"{self.userservice}/public/web/login"

    def mfa_url(self):
        return f"{self.userservice}/public/web/verify-two-factor"

    def refresh_url(self):
        return f"{self.userservice}/public/web/token-refresh"

    def portfolio_url(self, account_uuid):
        return f"{self.prodapi}/hstier1service/account/{account_uuid}/portfolio"

    def account_history_url(self, account_uuid):
        return f"{self.prodapi}/hstier2service/history?accountUuids={account_uuid}"

    def get_quote_url(self, symbol):
        return f"{self.prodapi}/marketdataservice/stockcharts/last-trade/{symbol}"

    def get_crypto_quote_url(self, symbol):
        return f"{self.prodapi}/cryptoservice/quotes?symbols={symbol}"

    def get_order_quote(self, symbol):
        return f"{self.prodapi}/tradingservice/quote/equity/{symbol}"

    def build_order_url(self, account_uuid):
        return f"{self.ordergateway}/accounts/{account_uuid}/orders"

    def preflight_order_url(self, account_uuid):
        return f"{self.ordergateway}/accounts/{account_uuid}/orders/preflight"

    def submit_put_order_url(self, account_uuid, order_id):
        return f"{self.ordergateway}/accounts/{account_uuid}/orders/{order_id}"

    def submit_get_order_url(self, account_uuid, order_id):
        return f"{self.prodapi}/hstier1service/account/{account_uuid}/order/{order_id}"

    def get_pending_orders_url(self, account_uuid):
        return f"{self.prodapi}/hstier2service/history?&&status=PENDING&type=ALL&accountUuids={account_uuid}"

    def cancel_pending_order_url(self, account_uuid, order_id):
        return f"{self.ordergateway}/accounts/{account_uuid}/orders/{order_id}"

    def build_headers(self, auth=None, prodApi=False):
        headers = {
            "authority": "public.com",
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.8",
            "content-type": "application/json",
            "origin": "https://public.com",
            "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Brave";v="132"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "sec-gpc": "1",
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "x-app-version": "web-1.0.11",
        }
        if auth is not None:
            headers["authorization"] = auth
        if prodApi:
            headers["authority"] = self.prodapi.replace("https://", "")
            headers["sec-fetch-site"] = "cross-site"
        return headers

    @staticmethod
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
