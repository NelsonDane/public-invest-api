import json


class Endpoints:
    def __init__(self):
        self.baseurl = "https://public.com"
        self.prodapi = "https://prod-api.154310543964.hellopublic.com"
        self.ordergateway = f"{self.prodapi}/customerordergateway"
        self.userservice = f"{self.baseurl}/userservice"

    def login_url(self) -> str:
        """Returns the login URL.

        Returns:
            The login endpoint URL.
        """
        return f"{self.userservice}/public/web/login"

    def mfa_url(self) -> str:
        """Returns the multi-factor authentication (MFA) URL.

        Returns:
            The MFA endpoint URL.
        """
        return f"{self.userservice}/public/web/verify-two-factor"

    def refresh_url(self) -> str:
        """Returns the token refresh URL.

        Returns:
            The token refresh endpoint URL.
        """
        return f"{self.userservice}/public/web/token-refresh"

    def portfolio_url(self, account_uuid: str) -> str:
        """Constructs the portfolio URL for a given account UUID.

        Args:
            account_uuid: The unique identifier for the account.
        Returns:
            The portfolio endpoint URL.
        """
        return f"{self.prodapi}/hstier1service/account/{account_uuid}/portfolio"

    def account_history_url(self, account_uuid: str) -> str:
        """Constructs the account history URL for a given account UUID.

        Args:
            account_uuid: The unique identifier for the account.
        Returns:
            The account history endpoint URL.
        """
        return f"{self.prodapi}/hstier2service/history?accountUuids={account_uuid}"

    def get_quote_url(self, symbol: str) -> str:
        """Constructs the URL for fetching a stock quote.

        Args:
            symbol: The stock symbol.
        Returns:
            The stock quote endpoint URL.
        """
        return f"{self.prodapi}/tradingservice/quote/equity/{symbol}"

    def get_crypto_quote_url(self, symbol: str) -> str:
        """Constructs the URL for fetching a cryptocurrency quote.

        Args:
            symbol: The cryptocurrency symbol.
        Returns:
            The crypto quote endpoint URL.
        """
        return f"{self.prodapi}/cryptoservice/quotes?symbols={symbol}"

    def preflight_order_url(self, account_uuid: str) -> str:
        """Constructs the URL for preflight order validation.

        Args:
            account_uuid: The unique identifier for the account.
        Returns:
            The preflight order endpoint URL.
        """
        return f"{self.ordergateway}/accounts/{account_uuid}/orders/preflight"

    def build_order_url(self, account_uuid: str) -> str:
        """Constructs the URL for building an order.

        Args:
            account_uuid: The unique identifier for the account.
        Returns:
            The build order endpoint URL.
        """
        return f"{self.ordergateway}/accounts/{account_uuid}/orders"

    def submit_put_order_url(self, account_uuid: str, order_id: str) -> str:
        """Constructs the URL for submitting a PUT order.

        Args:
            account_uuid: The unique identifier for the account.
            order_id: The unique identifier for the order.
        Returns:
            The submit PUT order endpoint URL.
        """
        return f"{self.ordergateway}/accounts/{account_uuid}/orders/{order_id}"

    def submit_get_order_url(self, account_uuid: str, order_id: str) -> str:
        """Constructs the URL for submitting a GET order.

        Args:
            account_uuid: The unique identifier for the account.
            order_id: The unique identifier for the order.
        Returns:
            The submit GET order endpoint URL.
        """
        return f"{self.prodapi}/hstier1service/account/{account_uuid}/order/{order_id}"

    def get_pending_orders_url(self, account_uuid: str) -> str:
        """Constructs the URL for fetching pending orders.

        Args:
            account_uuid: The unique identifier for the account.
        Returns:
            The pending orders endpoint URL.
        """
        return f"{self.prodapi}/hstier2service/history?&&status=PENDING&type=ALL&accountUuids={account_uuid}"

    def cancel_pending_order_url(self, account_uuid: str, order_id: str) -> str:
        """Constructs the URL for canceling a pending order.

        Args:
            account_uuid: The unique identifier for the account.
            order_id: The unique identifier for the order.
        Returns:
            The cancel pending order endpoint URL.
        """
        return f"{self.ordergateway}/accounts/{account_uuid}/orders/{order_id}"

    def contract_details_url(self, option_symbol: str) -> str:
        """Constructs the URL for fetching contract details.

        Args:
            option_symbol: The symbol of the option.
        Returns:
            The contract details endpoint URL.
        """
        return f"{self.prodapi}/hstier1service/contract-details/{option_symbol}/BUY"

    def build_headers(self, auth: bool = None, prodApi: bool = False) -> dict:
        """Builds HTTP headers for API requests.

        Args:
            auth: Authorization token.
            prodApi: Whether to use the production API authority.
        Returns:
            A dictionary containing HTTP headers.
        """
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
    def build_payload(email: str, password: str, code: str = None) -> str:
        """Builds JSON payload for authentication requests.

        Args:
            email: The user's email address.
            password: The user's password.
            code: The MFA verification code.
        Returns:
            A JSON-encoded payload string.
        """
        payload = {
            "email": email,
            "password": password,
        }
        if code is None:
            payload["stayLoggedIn"] = True
        else:
            payload["verificationCode"] = code
        return json.dumps(payload)
