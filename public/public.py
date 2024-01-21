import json
import os

import requests

from . import endpoints


def login_required(func):
    def wrapper(self, *args, **kwargs):
        if self.access_token is None:
            raise Exception("Login required")
        return func(self, *args, **kwargs)

    return wrapper


class Public:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(endpoints.build_headers())
        self.access_token = None
        self.account_uuid = None
        self.account_number = None
        self.all_login_info = None
        self.timeout = 10

    def _save_cookies(self, filename=None, path=None):
        if filename is None:
            filename = "public_credentials.json"
        if path is not None:
            filename = os.path.join(path, filename)
        with open(filename, "w") as f:
            json.dump(self.session.cookies.get_dict(), f)

    @staticmethod
    def _load_cookies(filename=None, path=None):
        if filename is None:
            filename = "public_credentials.json"
        if path is not None:
            filename = os.path.join(path, filename)
        if not os.path.exists(filename):
            return None
        with open(filename, "r") as f:
            return json.load(f)

    def _clear_cookies(self, filename=None, path=None):
        if filename is None:
            filename = "public_credentials.json"
        if path is not None:
            filename = os.path.join(path, filename)
        if os.path.exists(filename):
            os.remove(filename)
        self.session.cookies.clear()

    def login(self, username=None, password=None):
        if username is None or password is None:
            raise Exception("Username or password not provided")
        headers = self.session.headers
        payload = endpoints.build_payload(username, password)
        cookies = self._load_cookies()
        response = self.session.post(
            endpoints.login_url(),
            headers=headers,
            data=payload,
            timeout=self.timeout,
            cookies=cookies,
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
                cookies=cookies,
            )
            if response.status_code != 200:
                raise Exception("MFA Login failed, check credentials and code")
            response = self.session.post(
                endpoints.login_url(),
                headers=headers,
                data=payload,
                timeout=self.timeout,
                cookies=cookies,
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
    def place_order(
        symbol,
        quantity,
        side,
        order_type,
        time_in_force,
        limit_price=None,
        stop_price=None,
    ):
        raise NotImplementedError("Place order not implemented yet")
