import calendar
import os
import pickle
from datetime import datetime
from time import sleep

import requests

from public_invest_api.endpoints import Endpoints


def login_required(func):
    def wrapper(self, *args, **kwargs):
        """
        A wrapper function that checks if the user is logged in
        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        Raises:
            Exception: If the user is not logged in (i.e., access_token is None).
        Returns:
            The result of the function `func` if the user is logged in.
        """
        if self.access_token is None:
            raise Exception("Login required")
        return func(self, *args, **kwargs)

    return wrapper


def refresh_check(func):
    def wrapper(self, *args, **kwargs):
        """
        A wrapper function that checks if the access token needs to be refreshed
        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        Raises:
            Exception: If the access token refresh fails (i.e., response status code is not 200).
        Returns:
            The result of the function `func` if the access token does not need to be refreshed.
        """
        if self.expires_at is not None and datetime.now().timestamp() > self.expires_at:
            self._refresh_token()
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
        self.expires_at = None
        self.filename = "public_credentials.pkl"
        if filename is not None:
            self.filename = filename
        self.path = None
        if path is not None:
            self.path = path
        self._load_cookies()

    def _save_cookies(self) -> None:
        """
        Save cookies to file
        """
        filename = self.filename
        if self.path is not None:
            filename = os.path.join(self.path, filename)
        if self.path is not None and not os.path.exists(self.path):
            os.makedirs(self.path)
        with open(filename, "wb") as f:
            pickle.dump(self.session.cookies, f)

    def _load_cookies(self) -> bool:
        """
        Load cookies from file
        Returns:
            bool: True if cookies were loaded, False otherwise
        """
        filename = self.filename
        if self.path is not None:
            filename = os.path.join(self.path, filename)
        if not os.path.exists(filename):
            return False
        with open(filename, "rb") as f:
            self.session.cookies.update(pickle.load(f))
        return True

    def _clear_cookies(self) -> None:
        """
        Clear cookies and remove file
        """
        filename = self.filename
        if self.path is not None:
            filename = os.path.join(self.path, filename)
        if os.path.exists(filename):
            os.remove(filename)
        self.session.cookies.clear()

    def login(self, username=None, password=None, wait_for_2fa=True, code=None) -> dict:
        """
        Logs in to the Public.com API by making a POST request to the login URL.
        Args:
            username (str): The email to log in with.
            password (str): The password to log in with.
            wait_for_2fa (bool): Whether to wait for 2FA code to be entered or raise exception.
            code (str): The 2FA code to enter when re-calling login.
        Returns:
            dict: The JSON response from the login URL containing the access token.
        Raises:
            Exception: If the login fails (i.e., response status code is not 200).
        """
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
                # Perhaps cookies are expired
                self._clear_cookies()
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
        self.expires_at = (int(response["loginResponse"]["serverTime"]) / 1000) + int(response["loginResponse"]["expiresIn"])
        self.all_login_info = response
        self._save_cookies()
        return response

    @login_required
    def _refresh_token(self) -> dict:
        """
        Refreshes the access token by making a POST request to the refresh URL.
        Returns:
            dict: The JSON response from the refresh URL containing the new access token.
        Raises:
            Exception: If the token refresh fails (i.e., response status code is not 200 or 2FA is required).
        """
        headers = self.session.headers
        response = self.session.post(
            self.endpoints.refresh_url(), headers=headers, timeout=self.timeout
        )
        if response.status_code != 200:
            raise Exception("Token refresh failed")
        response = response.json()
        self.access_token = response["accessToken"]
        self.expires_at = (int(response["serverTime"]) / 1000) + int(response["expiresIn"])
        self.account_uuid = response["accounts"][0]["accountUuid"]
        self._save_cookies()
        return response

    @login_required
    @refresh_check
    def get_portfolio(self) -> dict:
        """
        Gets the user's portfolio by making a GET request to the portfolio URL.
        Returns:
            dict: The JSON response from the portfolio URL containing the user's portfolio.
        Raises:
            Exception: If the portfolio request fails (i.e., response status code is not 200).
        """
        headers = self.endpoints.build_headers(self.access_token, prodApi=True)
        portfolio = self.session.get(
            self.endpoints.portfolio_url(self.account_uuid),
            headers=headers,
            timeout=self.timeout,
        )
        if portfolio.status_code != 200:
            raise Exception(f"Portfolio request failed: {portfolio.text}")
        return portfolio.json()

    @staticmethod
    def _history_filter_date(date: str) -> dict:
        """
        Returns the start and end date for the given date range.
        Args:
            date (str): The date range (all, current_month, last_month, this_year, last_year).
        Returns:
            dict: The start and end date for the given date range in the format yyyy-mm-dd.
        """
        if date == "all":
            return {}
        now = datetime.now()
        if date == "current_month":
            start_date = datetime(now.year, now.month, 1)
            end_date = datetime(
                now.year, now.month, calendar.monthrange(now.year, now.month)[1]
            )
        elif date == "last_month":
            start_date = datetime(now.year, now.month - 1, 1)
            end_date = datetime(
                now.year, now.month - 1, calendar.monthrange(now.year, now.month - 1)[1]
            )
        elif date == "this_year":
            start_date = datetime(now.year, 1, 1)
            end_date = datetime(now.year, 12, 31)
        elif date == "last_year":
            start_date = datetime(now.year - 1, 1, 1)
            end_date = datetime(now.year - 1, 12, 31)
        return {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d"),
        }

    @login_required
    @refresh_check
    def get_account_history(
        self,
        date="all",
        asset_class="all",
        min_amount=None,
        max_amount=None,
        transaction_type="all",
        status="all",
        nextToken=None,
    ) -> dict:
        """
        Returns the user's account history from https://public.com/settings/history.
        The filters match the filters on the website.
        Args:
            date (str, optional): The date range (all, current_month, last_month, this_year, last_year).
            asset_class (str or list, optional): The asset class (all, stocks_and_etfs, options, bonds, crypto). For multiple, pass a list: ["stocks_and_etfs", "options"].
            min_amount (int, optional): The minimum amount. If both min_amount and max_amount are None, no filter is applied.
            max_amount (int, optional): The maximum amount. If both min_amount and max_amount are None, no filter is applied.
            transaction_type (str or list, optional): The transaction type (all, buy, sell, multi_leg, deposit, withdrawal, 6m_treasury_bills, acat, option_event, interest_dividend_maturity, reward, subscription, misc). For multiple, pass a list: ["buy", "sell"].
            status (str or list, optional): The status (all, completed, rejected, cancelled, pending). For multiple, pass a list: ["completed", "rejected"].
        Returns:
            dict: The JSON response from the account history URL containing the user's account history.
                - pendingTransactions (list): A list of pending transactions.
                - transactions (list): A list of transactions.
                - accountCreated (bool?): Whether the account was created? Not sure, mine is null.
                - nextToken (str): The next token for pagination.
        Raises:
            Exception: If the account history request fails (i.e., response status code is not 200).
        """
        headers = self.endpoints.build_headers(self.access_token)
        url = self.endpoints.account_history_url(self.account_uuid)
        params = {}
        # Verifications
        if date not in ["all", "current_month", "last_month", "this_year", "last_year"]:
            raise Exception(f"Invalid date: {date}")
        if asset_class != "all":
            if not isinstance(asset_class, list):
                asset_class = [asset_class]
            for asset in asset_class:
                if asset not in [
                    "all",
                    "stocks_and_etfs",
                    "options",
                    "bonds",
                    "crypto",
                ]:
                    raise Exception(f"Invalid asset class: {asset}")
        if min_amount is not None and not isinstance(min_amount, int):
            raise Exception("Invalid min amount. Must be int.")
        if max_amount is not None and not isinstance(max_amount, int):
            raise Exception("Invalid max amount. Must be int.")
        if transaction_type != "all":
            if not isinstance(transaction_type, list):
                transaction_type = [transaction_type]
            for t in transaction_type:
                if t not in [
                    "all",
                    "buy",
                    "sell",
                    "multi_leg",
                    "deposit",
                    "withdrawal",
                    "6m_treasury_bills",
                    "acat",
                    "option_event",
                    "interest_dividend_maturity",
                    "reward",
                    "subscription",
                    "misc",
                ]:
                    raise Exception(f"Invalid type: {t}")
        if status != "all":
            if not isinstance(status, list):
                status = [status]
            for s in status:
                if s not in ["all", "completed", "rejected", "cancelled", "pending"]:
                    raise Exception(f"Invalid status: {s}")
        # Date filter
        date_params = self._history_filter_date(date)
        if date_params != {}:
            params.update(date_params)
        # Asset class filter
        if asset_class != "all":
            asset_class_map = {
                "stocks_and_etfs": "EQUITY",
                "options": "OPTION",
                "bonds": "BOND",
                "crypto": "CRYPTO",
            }
            params["assetClass"] = [asset_class_map[asset] for asset in asset_class]
        # Amount filter
        if min_amount is not None:
            params["amountGreaterThanEqualTo"] = min_amount
        if max_amount is not None:
            params["amountLessThanEqualTo"] = max_amount
        # Type filter
        if transaction_type != "all":
            type_map = {
                "buy": "PURCHASE",
                "sell": "SALE",
                "multi_leg": "MULTI_LEG_ORDER",
                "deposit": "DEPOSIT",
                "withdrawal": "WITHDRAWAL",
                "6m_treasury_bills": "TREASURY_ACCOUNT_TRANSFER",
                "acat": "ACAT",
                "option_event": "OPTION_EVENTS",
                "interest_dividend_maturity": "INTEREST",
                "reward": "STOCK_REWARD",
                "subscription": "SUBSCRIPTION",
                "misc": "OTHER",
            }
            params["type"] = [type_map[t] for t in transaction_type]
        # Status filter
        if status != "all":
            params["status"] = [s.upper() for s in status]
        # Next token
        if nextToken is not None:
            params["nextToken"] = nextToken
        # Make the request
        response = self.session.get(
            url, headers=headers, params=params, timeout=self.timeout
        )
        if response.status_code != 200:
            raise Exception(f"Account history request failed: {response.text}")
        return response.json()

    @login_required
    def get_account_number(self) -> str:
        """
        Gets the user's account number.
        Returns:
            str: The user's account number.
        """
        return self.account_number

    @login_required
    def get_positions(self) -> list:
        """
        Gets the user's positions by making a GET request to the positions URL.
        Returns:
            list: The JSON response from the positions URL containing the user's positions.
        Raises:
            Exception: If the positions request fails (i.e., response status code is not 200).
        """
        account_info = self.get_portfolio()
        return account_info["positions"]

    @login_required
    def is_stock_owned(self, symbol) -> bool:
        """
        Checks if the user owns a stock by checking the user's positions.
        Args:
            symbol (str): The stock symbol to check.
        Returns:
            bool: True if the user owns the stock, False otherwise.
        """
        positions = self.get_positions()
        for position in positions:
            if position["instrument"]["symbol"] == symbol:
                return True
        return False

    @login_required
    def get_owned_stock_quantity(self, symbol) -> float | None:
        """
        Gets the quantity of a stock owned by the user.
        Args:
            symbol (str): The stock symbol to check.
        Returns:
            float: The quantity of the stock owned by the user.
        Raises:
            Exception: If the stock is not owned by the user.
        """
        if not self.is_stock_owned(symbol):
            raise Exception(f"Stock {symbol} is not owned")
        positions = self.get_positions()
        for position in positions:
            if position["instrument"]["symbol"] == symbol:
                return float(position["quantity"])
        return None

    @login_required
    def get_account_type(self) -> str:
        """
        Gets the user's account type.
        Returns:
            str: The user's account type.
        """
        return self.all_login_info["loginResponse"]["accounts"][0]["type"]

    @login_required
    def get_account_cash(self) -> float:
        """
        Gets the user's account cash balance.
        Returns:
            float: The user's account cash balance.
        """
        account_info = self.get_portfolio()
        return account_info["equity"]["cash"]

    @login_required
    @refresh_check
    def get_symbol_price(self, symbol) -> float:
        """
        Gets the price of a stock by making a GET request to the quote URL.
        Args:
            symbol (str): The stock symbol to get the price of.
        Returns:
            float: The price of the stock.
        Raises:
            Exception: If the quote request fails (i.e., response status code is not 200).
        """
        headers = self.endpoints.build_headers(self.access_token)
        url = self.endpoints.get_quote_url(symbol)
        if "CRYPTO" in symbol:
            url = self.endpoints.get_crypto_quote_url(symbol)
        response = self.session.get(url, headers=headers, timeout=self.timeout)
        if response.status_code != 200:
            raise Exception(f"Quote request failed: {response.text}")
        if "CRYPTO" in symbol:
            return response.json()["quotes"][0]["last"]
        return response.json()["price"]

    @login_required
    @refresh_check
    def get_order_quote(self, symbol) -> dict:
        """
        Gets a quote for an order by making a GET request to the order quote URL.
        Args:
            symbol (str): The stock symbol to get the order quote for.
        Returns:
            dict: The JSON response from the order quote URL containing the order quote.
        Raises:
            Exception: If the quote request fails (i.e., response status code is not 200).
        """
        headers = self.endpoints.build_headers(self.access_token)
        response = self.session.get(
            self.endpoints.get_order_quote(symbol),
            headers=headers,
            timeout=self.timeout,
        )
        if response.status_code != 200:
            raise Exception(f"Quote request failed: {response.text}")
        return response.json()

    @login_required
    @refresh_check
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
    ) -> dict:
        """
        Places an order by making a POST request to the build order URL.
        Args:
            symbol (str): The stock symbol to place the order for.
            quantity (float): The quantity of the stock to buy or sell, or "all" to sell all owned stock.
            side (str): The side of the order (BUY or SELL).
            order_type (str): The type of the order (MARKET, LIMIT, or STOP).
            time_in_force (str): The time in force of the order (DAY, GTC, IOC, or FOK).
            limit_price (float): The limit price of the order (required for limit orders).
            is_dry_run (bool): Whether to simulate the order without submitting it.
            tip (float): The tip amount for the order.
        Returns:
            dict: The JSON response from the build order URL containing the order details.
        Raises:
            Exception: If the order fails (i.e., response status code is not 200).
        """
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
        # If sell, check safeguards
        if side == "SELL":
            if not self.is_stock_owned(symbol):
                raise Exception(f"Stock {symbol} is not owned")
            if isinstance(quantity, str) and quantity.lower() == "all":
                quantity = self.get_owned_stock_quantity(symbol)
            if quantity > self.get_owned_stock_quantity(symbol):
                raise Exception(f"Quantity exceeds owned stock for {symbol}")
        # What are they doing?
        if side == "BUY" and isinstance(quantity, str) and quantity.lower() == "all":
            raise Exception("Cannot buy all stock")
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
    @refresh_check
    def get_pending_orders(self) -> dict:
        """
        Gets the user's pending orders by making a GET request to the pending orders URL.
        Returns:
            dict: The JSON response from the pending orders URL containing the user's pending orders.
        Raises:
            Exception: If the pending orders request fails (i.e., response status code is not 200).
        """
        headers = self.endpoints.build_headers(self.access_token)
        response = self.session.get(
            self.endpoints.get_pending_orders_url(self.account_uuid),
            headers=headers,
            timeout=self.timeout,
        )
        if response.status_code != 200:
            raise Exception(f"Pending orders request failed: {response.text}")
        return response.json()

    @login_required
    @refresh_check
    def cancel_order(self, order_id) -> dict:
        """
        Cancels an order by making a DELETE request to the cancel order URL.
        Args:
            order_id (str): The order ID to cancel.
        Returns:
            dict: The JSON response from the cancel order URL containing the order details.
        Raises:
            Exception: If the cancel order fails (i.e., response status code is not 200).
        """
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
            raise Exception(f"Cancel order failed: {response.text}")
        return response.json()
