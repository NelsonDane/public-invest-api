import os
import pickle
from time import sleep

import requests

from public_invest_api.endpoints import Endpoints


def login_required(func):
    def wrapper(self, *args, **kwargs):
        if self.access_token is None:
            raise Exception("Login required")
        return func(self, *args, **kwargs)

    return wrapper


class Public:
    def __init__(self, filename=None, path=None):
        self.session = requests.Session()
        self.endpoints = Endpoints()
        self.session.headers.update(self.endpoints.build_headers())
        self.access_token = None
        self.account_uuid = None
        self.account_number = None
        self.all_login_info = None
        self.timeout = 10
        self.filename = "public_credentials.pkl"
        if filename is not None:
            self.filename = filename
        self.path = None
        if path is not None:
            self.path = path
        self._load_cookies()

    def _save_cookies(self):
        filename = self.filename
        if self.path is not None:
            filename = os.path.join(self.path, filename)
        if self.path is not None and not os.path.exists(self.path):
            os.makedirs(self.path)
        with open(filename, "wb") as f:
            pickle.dump(self.session.cookies, f)

    def _load_cookies(self):
        filename = self.filename
        if self.path is not None:
            filename = os.path.join(self.path, filename)
        if not os.path.exists(filename):
            return False
        with open(filename, "rb") as f:
            self.session.cookies.update(pickle.load(f))
        return True

    def _clear_cookies(self):
        filename = self.filename
        if self.path is not None:
            filename = os.path.join(self.path, filename)
        if os.path.exists(filename):
            os.remove(filename)
        self.session.cookies.clear()

    def login(self, username=None, password=None, wait_for_2fa=True, code=None):
        if username is None or password is None:
            raise Exception("Username or password not provided")
        headers = self.session.headers
        need_2fa = True
        if code is None:
            payload = self.endpoints.build_payload(username, password)
            self._load_cookies()
            response = self.session.post(
                self.endpoints.login_url(),
                headers=headers,
                data=payload,
                timeout=self.timeout,
            )
            if response.status_code != 200:
                print(response.text)
                raise Exception("Login failed, check credentials")
            response = response.json()
            if response["twoFactorResponse"] is not None:
                self._clear_cookies()
                phone = response["twoFactorResponse"]["maskedPhoneNumber"]
                print(f"2FA required, code sent to phone number {phone}...")
                if not wait_for_2fa:
                    raise Exception("2FA required: please provide code")
                code = input("Enter code: ")
            else:
                need_2fa = False
        if need_2fa:
            payload = self.endpoints.build_payload(username, password, code)
            response = self.session.post(
                self.endpoints.mfa_url(),
                headers=headers,
                data=payload,
                timeout=self.timeout,
            )
            if response.status_code != 200:
                raise Exception("MFA Login failed, check credentials and code")
            response = self.session.post(
                self.endpoints.login_url(),
                headers=headers,
                data=payload,
                timeout=self.timeout,
            )
            if response.status_code != 200:
                raise Exception("Login failed, check credentials")
            response = response.json()
        self.access_token = response["loginResponse"]["accessToken"]
        self.account_uuid = response["loginResponse"]["accounts"][0]["accountUuid"]
        self.account_number = response["loginResponse"]["accounts"][0]["account"]
        self.all_login_info = response
        self._save_cookies()
        return response

    @login_required
    def _refresh_token(self):
        headers = self.session.headers
        response = self.session.post(
            self.endpoints.refresh_url(), headers=headers, timeout=self.timeout
        )
        if response.status_code != 200:
            raise Exception("Token refresh failed")
        response = response.json()
        self.access_token = response["accessToken"]
        self._save_cookies()
        return response

    @login_required
    def get_portfolio(self):
        headers = self.endpoints.build_headers(self.access_token)
        portfolio = self.session.get(
            self.endpoints.portfolio_url(self.account_uuid),
            headers=headers,
            timeout=self.timeout,
        )
        if portfolio.status_code != 200:
            print(f"Portfolio request failed: {portfolio.text}")
            return None
        return portfolio.json()

    @login_required
    def get_account_number(self):
        return self.account_number

    @login_required
    def get_positions(self):
        account_info = self.get_portfolio()
        return account_info["positions"]

    @login_required
    def get_account_type(self):
        return self.all_login_info["loginResponse"]["accounts"][0]["type"]

    @login_required
    def get_account_cash(self):
        account_info = self.get_portfolio()
        if account_info is None:
            return None
        return account_info["equity"]["cash"]

    @login_required
    def get_symbol_price(self, symbol):
        headers = self.endpoints.build_headers(self.access_token)
        url = self.endpoints.get_quote_url(symbol)
        if "CRYPTO" in symbol:
            url = self.endpoints.get_crypto_quote_url(symbol)
        response = self.session.get(url, headers=headers, timeout=self.timeout)
        if response.status_code != 200:
            return None
        if "CRYPTO" in symbol:
            return response.json()["quotes"][0]["last"]
        return response.json()["price"]

    @login_required
    def get_order_quote(self, symbol):
        headers = self.endpoints.build_headers(self.access_token)
        response = self.session.get(
            self.endpoints.get_order_quote(symbol),
            headers=headers,
            timeout=self.timeout,
        )
        if response.status_code != 200:
            return None
        return response.json()

    @login_required
    def place_order(
        self,
        symbol,
        quantity,
        side,
        order_type,
        time_in_force,
        limit_price=None,
        is_dry_run=False,
        tip=None,
    ):
        headers = self.endpoints.build_headers(self.access_token, prodApi=True)
        symbol = symbol.upper()
        time_in_force = time_in_force.upper()
        order_type = order_type.upper()
        side = side.upper()
        if time_in_force not in ["DAY", "GTC", "IOC", "FOK"]:
            raise Exception(f"Invalid time in force: {time_in_force}")
        if order_type not in ["MARKET", "LIMIT", "STOP"]:
            raise Exception(f"Invalid order type: {order_type}")
        if side not in ["BUY", "SELL"]:
            raise Exception(f"Invalid side: {side}")
        if tip == 0:
            tip = None
        # Need to get quote first
        quote = self.get_order_quote(symbol)
        if quote is None:
            raise Exception(f"Quote not found for {symbol}")
        payload = {
            "symbol": symbol,
            "orderSide": side,
            "type": order_type,
            "timeInForce": time_in_force,
            "quote": quote,
            "quantity": quantity,
            "tipAmount": tip,
        }
        if order_type == "LIMIT":
            if limit_price is None:
                raise Exception("Limit price required for limit orders")
            payload["limitPrice"] = float(limit_price)
        # Preflight order endpoint
        preflight = self.session.post(
            self.endpoints.preflight_order_url(self.account_uuid),
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        if preflight.status_code != 200:
            raise Exception(f"Preflight failed: {preflight.text}")
        preflight = preflight.json()
        # Build order endpoint
        build_response = self.session.post(
            self.endpoints.build_order_url(self.account_uuid),
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        if build_response.status_code != 200:
            raise Exception(f"Build order failed: {build_response.text}")
        build_response = build_response.json()
        if build_response.get("orderId") is None:
            raise Exception(f"No order ID: {build_response}")
        order_id = build_response["orderId"]
        # Submit order with put
        if not is_dry_run:
            submit_response = self.session.put(
                self.endpoints.submit_put_order_url(self.account_uuid, order_id),
                headers=headers,
                timeout=self.timeout,
            )
            if submit_response.status_code != 200:
                raise Exception(f"Submit order failed: {submit_response.text}")
            submit_response = submit_response.json()
            # Empty dict is success
            if submit_response != {}:
                raise Exception(f"Order failed: {submit_response}")
            sleep(1)
        # Check if order was rejected
        check_response = self.session.get(
            self.endpoints.submit_get_order_url(self.account_uuid, order_id),
            headers=headers,
            timeout=self.timeout,
        )
        check_response = check_response.json()
        check_response["success"] = False
        # Order doesn't always fill immediately, but one of these should work
        if check_response["rejectionDetails"] is None:
            check_response["success"] = True
        if check_response["status"] == "FILLED":
            check_response["success"] = True
        return check_response

    @login_required
    def get_pending_orders(self):
        headers = self.endpoints.build_headers(self.access_token)
        response = self.session.get(
            self.endpoints.get_pending_orders_url(self.account_uuid),
            headers=headers,
            timeout=self.timeout,
        )
        if response.status_code != 200:
            return None
        return response.json()

    @login_required
    def cancel_order(self, order_id):
        headers = self.endpoints.build_headers(self.access_token)
        preflight = self.session.options(
            self.endpoints.cancel_pending_order_url(self.account_uuid, order_id),
            headers=headers,
            timeout=self.timeout,
        )
        if preflight.status_code != 200:
            raise Exception(f"Preflight failed: {preflight.text}")

        response = self.session.delete(
            self.endpoints.cancel_pending_order_url(self.account_uuid, order_id),
            headers=headers,
            timeout=self.timeout,
        )
        if response.status_code != 200:
            return None
        return response.json()
