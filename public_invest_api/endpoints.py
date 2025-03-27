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
        return f"{self.prodapi}/marketdataservice/stockcharts/last-trade/{symbol}"

    def get_crypto_quote_url(self, symbol: str) -> str:
        """Constructs the URL for fetching a cryptocurrency quote.

        Args:
            symbol: The cryptocurrency symbol.
        Returns:
            The crypto quote endpoint URL.
        """
        return f"{self.prodapi}/cryptoservice/quotes?symbols={symbol}"

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
