import calendar
import functools
import os
import pickle
from datetime import datetime
from time import sleep

import requests

from public_invest_api.endpoints import Endpoints


def _login_required(func):
    """Decorator to check if user is logged in by checking if access token is None.

    Args:
        func: The function to wrap.
    Returns:
        The wrapped function.
    Raises:
        Exception: If the user is not logged in.
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.access_token is None:
            raise Exception("Login required")
        return func(self, *args, **kwargs)

    return wrapper


def _refresh_check(func):
    """Decorator to check if the access token is expired and refresh it if necessary.

    Args:
        func: The function to wrap.
    Returns:
        The wrapped function.
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.expires_at is not None and datetime.now().timestamp() > self.expires_at:
            self._refresh_token()
        return func(self, *args, **kwargs)

    return wrapper


class Public:
    """Initializes the Public.com API client.

    Args:
        filename: The filename to save the cookies to. Defaults to "public_credentials.pkl".
        path: The path to save the cookies to. Defaults to current directory.
    """

    def __init__(self, filename: str = "public_credentials.pkl", path: str = None):
        self.session = requests.Session()
        self.endpoints = Endpoints()
        self.session.headers.update(self.endpoints.build_headers())
        self.access_token = None
        self.account_uuid = None
        self.account_number = None
        self.all_login_info = None
        self.timeout = 10
        self.expires_at = None
        self.filename = filename
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
        """Load cookies from file

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

    def login(
        self,
        username: str = None,
        password: str = None,
        wait_for_2fa: str = True,
        code: str = None,
    ) -> dict:
        """Logs in to the Public.com API by making a POST request to the login URL.

        Args:
            username: The email to log in with.
            password: The password to log in with.
            wait_for_2fa: Whether to wait for 2FA code to be entered or raise exception.
            code: The 2FA code to enter when re-calling login.
        Returns:
            The JSON response from the login URL containing the access token.
        Raises:
            Exception: If the login fails (i.e., response status code is not 200).
        """
        if username is None or password is None:
            raise Exception("Username or password not provided")
        # See if we can refresh login
        refresh_success = False
        try:
            response = self._refresh_token()
            refresh_success = True
        except Exception:
            pass
        headers = self.session.headers
        need_2fa = True
        if code is None and not refresh_success:
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
        if need_2fa and not refresh_success:
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
        # Get info from response
        if "loginResponse" in response:
            response = response["loginResponse"]
        self.access_token = response["accessToken"]
        self.account_uuid = response["accounts"][0]["accountUuid"]
        self.account_number = response["accounts"][0]["account"]
        self.expires_at = (int(response["serverTime"]) / 1000) + int(
            response["expiresIn"]
        )
        self.all_login_info = response
        self._save_cookies()
        return response

    def _refresh_token(self) -> dict:
        """Refreshes the access token by making a POST request to the refresh URL.

        Returns:
            The JSON response from the refresh URL containing the new access token.
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
        self.expires_at = (int(response["serverTime"]) / 1000) + int(
            response["expiresIn"]
        )
        self.account_uuid = response["accounts"][0]["accountUuid"]
        self._save_cookies()
        return response

    @_login_required
    @_refresh_check
    def get_portfolio(self) -> dict:
        """Gets the user's portfolio by making a GET request to the portfolio URL.

        Returns:
            The JSON response from the portfolio URL containing the user's portfolio.
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
        """Returns the start and end date for the given date range.

        Args:
            date The date range (all, current_month, last_month, this_year, last_year).
        Returns:
            The start and end date for the given date range in the format yyyy-mm-dd.
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
            "dateFrom": start_date.strftime("%Y-%m-%d"),
            "dateTo": end_date.strftime("%Y-%m-%d"),
        }

    @_login_required
    @_refresh_check
    def get_account_history(
        self,
        date: str = "all",
        asset_class: str = "all",
        min_amount: int = None,
        max_amount: int = None,
        transaction_type: str | list = "all",
        status: str | list = "all",
        nextToken: str = None,
    ) -> dict:
        """Returns the user's account history from https://public.com/settings/history.
        The filters match the filters on the website.

        Args:
            date: The date range (all, current_month, last_month, this_year, last_year).
            asset_class: The asset class (all, stocks_and_etfs, options, bonds, crypto). For multiple, pass a list: ["stocks_and_etfs", "options"].
            min_amount: The minimum amount. If both min_amount and max_amount are None, no filter is applied.
            max_amount: The maximum amount. If both min_amount and max_amount are None, no filter is applied.
            transaction_type: The transaction type (all, buy, sell, multi_leg, deposit, withdrawal, 6m_treasury_bills, acat, option_event, interest_dividend_maturity, reward, subscription, misc). For multiple, pass a list: ["buy", "sell"].
            status: The status (all, completed, rejected, cancelled, pending). For multiple, pass a list: ["completed", "rejected"].
            nextToken: The next token for pagination.
        Returns:
            The JSON response from the account history URL containing the user's account history with keys:
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

    @_login_required
    def get_account_number(self) -> str:
        """Gets the user's account number.

        Returns:
            The user's account number.
        """
        return self.account_number

    @_login_required
    def get_positions(self) -> list:
        """Gets the user's positions by making a GET request to the positions URL.

        Returns:
            The JSON response from the positions URL containing the user's positions.
        Raises:
            Exception: If the positions request fails (i.e., response status code is not 200).
        """
        account_info = self.get_portfolio()
        return account_info["positions"]

    @_login_required
    def is_stock_owned(self, symbol: str) -> bool:
        """Checks if the user owns a stock by checking the user's positions.

        Args:
            symbol: The stock symbol to check.
        Returns:
            True if the user owns the stock, False otherwise.
        """
        positions = self.get_positions()
        for position in positions:
            if position["instrument"]["symbol"] == symbol:
                return True
        return False

    @_login_required
    def get_owned_stock_quantity(self, symbol: str) -> float | None:
        """Gets the quantity of a stock owned by the user.

        Args:
            symbol: The stock symbol to check.
        Returns:
            The quantity of the stock owned by the user.
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

    @_login_required
    def get_account_type(self) -> str:
        """Gets the user's account type.

        Returns:
            The user's account type.
        """
        return self.all_login_info["accounts"][0]["type"]

    @_login_required
    def get_account_cash(self) -> float:
        """Gets the user's account cash balance.

        Returns:
            The user's account cash balance.
        """
        account_info = self.get_portfolio()
        return account_info["equity"]["cash"]

    @_login_required
    @_refresh_check
    def get_symbol_price(self, symbol: str) -> float:
        """Gets the price of a stock by making a GET request to the quote URL.

        Args:
            symbol: The stock symbol to get the price of.
        Returns:
            The price of the stock.
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
        return response.json()["last"]

    @_login_required
    @_refresh_check
    def get_order_quote(self, symbol: str) -> dict:
        """Gets a quote for an order by making a GET request to the order quote URL.

        Args:
            symbol: The stock symbol to get the order quote for.
        Returns:
            The JSON response from the order quote URL containing the order quote.
        Raises:
            Exception: If the quote request fails (i.e., response status code is not 200).
        """
        headers = self.endpoints.build_headers(self.access_token)
        response = self.session.get(
            self.endpoints.get_quote_url(symbol),
            headers=headers,
            timeout=self.timeout,
        )
        if response.status_code != 200:
            raise Exception(f"Quote request failed: {response.text}")
        return response.json()

    @_login_required
    @_refresh_check
    def place_order(
        self,
        symbol: str,
        quantity: float,
        side: str,
        order_type: str,
        time_in_force: str,
        limit_price: float = None,
        is_dry_run: bool = False,
        tip: float = None,
    ) -> dict:
        """Places an order by making a POST request to the build order URL.

        Args:
            symbol: The stock symbol to place the order for.
            quantity: The quantity of the stock to buy or sell, or "all" to sell all owned stock.
            side: The side of the order (BUY or SELL).
            order_type: The type of the order (MARKET, LIMIT, or STOP).
            time_in_force: The time in force of the order (DAY, GTC, IOC, or FOK).
            limit_price: The limit price of the order (required for limit orders).
            is_dry_run: Whether to simulate the order without submitting it.
            tip: The tip amount for the order.
        Returns:
            The JSON response from the build order URL containing the order details.
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

    @_login_required
    @_refresh_check
    def get_pending_orders(self) -> dict:
        """Gets the user's pending orders by making a GET request to the pending orders URL.

        Returns:
            The JSON response from the pending orders URL containing the user's pending orders.
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

    @_login_required
    @_refresh_check
    def cancel_order(self, order_id: str) -> dict:
        """Cancels an order by making a DELETE request to the cancel order URL.

        Args:
            order_id: The order ID to cancel.
        Returns:
            The JSON response from the cancel order URL containing the order details.
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

    @_login_required
    @_refresh_check
    def fetch_contract_details(self, symbol: str) -> dict:
        """Fetches contract details for the given option symbol

        Args:
            symbol: The option symbol to fetch contract details for.
        Returns:
            dict: The contract details for the given option symbol.
        Raises:
            Exception: If request fails (i.e., response status code is not 200).
            ValueError: If incomplete contract details are received.
        """
        headers = self.endpoints.build_headers(self.access_token)
        url = self.endpoints.contract_details_url(symbol)
        response = self.session.get(url, headers=headers, timeout=self.timeout)
        if response.status_code != 200:
            raise Exception(f"Error fetching contract details: {response.text}")
        contract_data = response.json()
        if not contract_data.get("details", {}).get("quote"):
            raise ValueError("Incomplete contract details received.")
        return contract_data

    @staticmethod
    def _build_option_symbol(
        stock_symbol: str, expiration_date: str, option_type: str, strike_price: float
    ) -> str:
        """Builds the option symbol for the given parameters.

        Args:
            stock_symbol: The stock symbol.
            expiration_date: The expiration date in the format "YYYY-MM-DD".
            option_type: The option type (CALL or PUT).
            strike_price: The strike price of the option.
        Returns:
            The option symbol for the given parameters.
        """
        formatted_strike = (
            f"{int(float(strike_price) * 1000):08d}"  # 8 digits padded, in cents
        )
        formatted_date = datetime.strptime(expiration_date, "%Y-%m-%d").strftime(
            "%y%m%d"
        )
        return f"{stock_symbol.upper()}{formatted_date}{option_type.upper()}{formatted_strike}-OPTION"

    @_login_required
    @_refresh_check
    def submit_options_order(
        self,
        symbol: str,
        quantity: float,
        limit_price: float,
        side: str = "BUY",
        time_in_force: str = "DAY",
        is_dry_run: bool = False,
        tip: float | None = None,
    ) -> dict:
        """Submits an options order by making a POST request to the build order URL.

        Args:
            symbol: The stock symbol to place the order for.
            quantity: The quantity of the stock to buy or sell.
            limit_price: The limit price of the order.
            side The side of the order (BUY or SELL).
            time_in_force: The time in force of the order (DAY, GTC, IOC, or FOK).
            is_dry_run: Whether to simulate the order without submitting it.
            tip: The tip amount for the order.
        Returns:
            The JSON response from the build order URL containing the order details.
        Raises:
            Exception: If the order fails (i.e., response status code is not 200).
        """
        headers = self.endpoints.build_headers(self.access_token, prodApi=True)
        symbol = symbol.upper()
        time_in_force = time_in_force.upper()
        side = side.upper()
        if time_in_force not in ["DAY", "GTC", "IOC", "FOK"]:
            raise Exception(f"Invalid time in force: {time_in_force}")
        if side not in ["BUY", "SELL"]:
            raise Exception(f"Invalid side: {side}")
        # Need to get details first
        contract_details = self.fetch_contract_details(symbol)
        if contract_details is None:
            raise Exception(f"Details not found for {symbol}")
        payload = {
            "symbol": symbol,
            "quantity": quantity,
            "orderSide": side,
            "type": "LIMIT",
            "timeInForce": time_in_force,
            "limitPrice": limit_price,
            "quote": contract_details["details"]["quote"],
            "openCloseIndicator": "OPEN" if side == "BUY" else "CLOSE",
            "dryRun": is_dry_run,
            "tip": tip,
        }
        # Preflight order endpoint
        preflight = self.session.post(
            self.endpoints.preflight_order_url(self.account_uuid),
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        if preflight.status_code != 200:
            raise Exception(f"Preflight failed: {preflight.text}")
        # Place the order
        response = self.session.post(
            self.endpoints.build_order_url(self.account_uuid),
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        if response.status_code != 200:
            raise Exception(f"Order submission error: {response.text}")
        build_response = response.json()
        # Submit the order (PUT) using the returned orderId
        order_id = build_response.get("orderId")
        if not order_id:
            raise Exception(f"No orderId returned: {build_response}")
        # Only submit if not a dry run
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
