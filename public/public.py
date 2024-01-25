import os

import requests
import pickle

from . import endpoints
from time import sleep


def login_required(func):
    def wrapper(self, *args, **kwargs):
        if self.access_token is None:
            raise Exception("Login required")
        return func(self, *args, **kwargs)

    return wrapper


class Public:
    def __init__(self, filename=None, path=None):
        self.session = requests.Session()
        self.session.headers.update(endpoints.build_headers())
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

    def login(self, username=None, password=None):
        if username is None or password is None:
            raise Exception("Username or password not provided")
        headers = self.session.headers
        payload = endpoints.build_payload(username, password)
        self._load_cookies()
        response = self.session.post(
            endpoints.login_url(),
            headers=headers,
            data=payload,
            timeout=self.timeout,
        )
        if response.status_code != 200:
            raise Exception("Login failed, check credentials")
        response = response.json()
        if response["twoFactorResponse"] is not None:
            self._clear_cookies()
            last_four = response["twoFactorResponse"]["phoneNumberLastFour"]
            print(f"2FA required, code sent to phone number ending in {last_four}...")
            code = input("Enter code: ")
            payload = endpoints.build_payload(username, password, code)
            response = self.session.post(
                endpoints.mfa_url(),
                headers=headers,
                data=payload,
                timeout=self.timeout,
            )
            if response.status_code != 200:
                raise Exception("MFA Login failed, check credentials and code")
            response = self.session.post(
                endpoints.login_url(),
                headers=headers,
                data=payload,
                timeout=self.timeout,
            )
            if response.status_code != 200:
                raise Exception("Here Login failed, check credentials")
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
            endpoints.refresh_url(), headers=headers, timeout=self.timeout
        )
        if response.status_code != 200:
            raise Exception("Token refresh failed")
        response = response.json()
        self.access_token = response["accessToken"]
        self._save_cookies()
        return response

    @login_required
    def get_portfolio(self):
        headers = endpoints.build_headers(self.access_token)
        portfolio = self.session.get(
            endpoints.portfolio_url(self.account_uuid),
            headers=headers,
            timeout=self.timeout,
        )
        if portfolio.status_code != 200:
            raise Exception("Portfolio request failed")
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
        return account_info["equity"]["cash"]

    @login_required
    def get_symbol_price(self, symbol):
        headers = endpoints.build_headers(self.access_token)
        response = self.session.get(
            endpoints.get_quote_url(symbol), headers=headers, timeout=self.timeout
        )
        if response.status_code == 400:
            return None
        if response.status_code != 200:
            raise Exception("Symbol price request failed")
        return response.json()["price"]

    @login_required
    def get_order_quote(self, symbol):
        headers = endpoints.build_headers(self.access_token)
        response = self.session.get(
            endpoints.get_order_quote(symbol), headers=headers, timeout=self.timeout
        )
        if response.status_code == 400:
            return None
        if response.status_code != 200:
            raise Exception("Symbol price request failed")
        return response.json()

    @login_required
    def place_order(
        self,
        symbol,
        quantity,
        side,
        order_type,
        time_in_force,
        is_dry_run=False,
        limit_price=None,
        stop_price=None,
        tip=None,
    ):
        # raise NotImplementedError("Place order not implemented yet")
        headers = endpoints.build_headers(self.access_token, prodApi=True)
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
        print(f"Quote: {quote}")
        payload = {
            "symbol": symbol,
            "orderSide": side,
            "type": order_type,
            "timeInForce": time_in_force,
            "quote": quote,
            "quantity": quantity,
            "tipAmount": tip,
        }
        # Preflight order endpoint
        preflight = self.session.post(
            endpoints.preflight_order_url(self.account_uuid),
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        preflight = preflight.json()
        print(f"Preflight response: {preflight}")
        # Build order endpoint
        build_response = self.session.post(
            endpoints.build_order_url(self.account_uuid),
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        build_response = build_response.json()
        print(f"Build order response: {build_response}")
        if build_response.get("orderId") is None:
            raise Exception(f"No order ID: {build_response}")
        order_id = build_response["orderId"]
        # Submit order with put
        print(f"Order ID: {order_id}")
        if not is_dry_run:
            submit_response = self.session.put(
                endpoints.submit_put_order_url(self.account_uuid, order_id),
                headers=headers,
                timeout=self.timeout,
            )
            submit_response = submit_response.json()
            # Empty dict is success
            if submit_response != {}:
                print(f"Submit response: {submit_response}")
                raise Exception(f"Order failed: {submit_response}")          
            sleep(1)
        # Check if order was rejected
        check_response = self.session.get(
            endpoints.submit_get_order_url(self.account_uuid, order_id),
            headers=headers,
            timeout=self.timeout,
        )
        check_response = check_response.json()
        print(f"Submit response: {check_response}")
        return check_response
