class Endpoints:
    """Class for building URL request endpoints."""

    def __init__(self) -> None:
        """Initialize the Endpoints class with base URLs for API services."""
        self.api = "https://api.public.com"
        self.api_auth_service = f"{self.api}/userapiauthservice"
        self.user_api_gateway = f"{self.api}/userapigateway"

    def jwt_url(self) -> str:
        """Return the Personal Access Token (JWT) endpoint URL.

        Returns:
            The JWT endpoint URL.

        """
        return f"{self.api_auth_service}/personal/access-tokens"

    def get_accounts_url(self) -> str:
        """Return the URL for retrieving user accounts.

        Returns:
            The accounts endpoint URL.

        """
        return f"{self.user_api_gateway}/trading/account"

    def get_account_portfolio_v2_url(self, account_id: str) -> str:
        """Return the URL for retrieving a user's portfolio.

        Args:
            account_id: The unique identifier for the user's account.

        Returns:
            The portfolio endpoint URL.

        """
        return f"{self.user_api_gateway}/trading/{account_id}/portfolio/v2"

    def get_history_url(self, account_id: str) -> str:
        """Return the URL for retrieving a user's account history.

        Args:
            account_id: The unique identifier for the user's account.

        Returns:
            The account history endpoint URL.

        """
        return f"{self.user_api_gateway}/trading/{account_id}/history"

    def get_all_instruments_url(self) -> str:
        """Return the URL for retrieving all available instruments.

        Returns:
            The instruments endpoint URL.

        """
        return f"{self.user_api_gateway}/trading/instruments"

    def get_instrument_url(self, symbol: str, symbol_type: str) -> str:
        """Return the URL for retrieving details of a specific instrument.

        Args:
            symbol: The symbol of the instrument (e.g., stock ticker).
            symbol_type: The type of the instrument (e.g., stock, option).

        Returns:
            The specific instrument endpoint URL.

        """
        return f"{self.user_api_gateway}/trading/instruments/{symbol}/{symbol_type}"

    def get_quotes_url(self, account_id: str) -> str:
        """Return the URL for retrieving quotes for specified symbols.

        Args:
            account_id: The unique identifier for the user's account.

        Returns:
            The quotes endpoint URL.

        """
        return f"{self.user_api_gateway}/marketdata/{account_id}/quotes"

    def get_options_expirations_url(self, account_id: str) -> str:
        """Return the URL for retrieving options expiration dates for a given symbol.

        Args:
            account_id: The unique identifier for the user's account.

        Returns:
            The options expiration dates endpoint URL.

        """
        return f"{self.user_api_gateway}/marketdata/{account_id}/options-expirations"

    def get_options_chain_url(self, account_id: str) -> str:
        """Return the URL for retrieving the options chain for a given symbol and expiration date.

        Args:
            account_id: The unique identifier for the user's account.

        Returns:
            The options chain endpoint URL.

        """
        return f"{self.user_api_gateway}/marketdata/{account_id}/options-chain"

    def preflight_single_leg_url(self, account_id: str) -> str:
        """Return the URL for preflighting a single-leg order.

        Args:
            account_id: The unique identifier for the user's account.

        Returns:
            The preflight single-leg order endpoint URL.

        """
        return f"{self.user_api_gateway}/trading/{account_id}/preflight/single-leg"

    def preflight_multi_leg_url(self, account_id: str) -> str:
        """Return the URL for preflighting a multi-leg order.

        Args:
            account_id: The unique identifier for the user's account.

        Returns:
            The preflight multi-leg order endpoint URL.

        """
        return f"{self.user_api_gateway}/trading/{account_id}/preflight/multi-leg"

    def place_order_url(self, account_id: str) -> str:
        """Return the URL for placing an order.

        Args:
            account_id: The unique identifier for the user's account.

        Returns:
            The place order endpoint URL.

        """
        return f"{self.user_api_gateway}/trading/{account_id}/order"

    def place_multi_leg_order_url(self, account_id: str) -> str:
        """Return the URL for placing a multi-leg order.

        Args:
            account_id: The unique identifier for the user's account.

        Returns:
            The place multi-leg order endpoint URL.

        """
        return f"{self.user_api_gateway}/trading/{account_id}/order/multileg"

    def get_order_url(self, account_id: str, order_id: str) -> str:
        """Return the URL for retrieving details of a specific order.

        Args:
            account_id: The unique identifier for the user's account.
            order_id: The unique identifier for the order.

        Returns:
            The specific order endpoint URL.

        """
        return f"{self.user_api_gateway}/trading/{account_id}/order/{order_id}"

    def cancel_order_url(self, account_id: str, order_id: str) -> str:
        """Return the URL for canceling a specific order.

        Args:
            account_id: The unique identifier for the user's account.
            order_id: The unique identifier for the order.

        Returns:
            The cancel order endpoint URL.

        """
        return f"{self.user_api_gateway}/trading/{account_id}/order/{order_id}"

    def get_option_greeks_url(self, account_id: str, osi_option_symbol: str) -> str:
        """Return the URL for retrieving option greeks for a given symbol and expiration date.

        Args:
            account_id: The unique identifier for the user's account.
            osi_option_symbol: The symbol of the option.

        Returns:
            The option greeks endpoint URL.

        """
        return f"{self.user_api_gateway}/order-details/{account_id}/{osi_option_symbol}/greeks"

    @staticmethod
    def build_headers(bearer: str | None = None) -> dict[str, str]:
        """Build HTTP headers for API requests.

        Args:
            bearer: Authorization token.

        Returns:
            A dictionary containing HTTP headers.

        """
        headers = {
            "Content-Type": "application/json",
        }
        if bearer is not None:
            headers["Authorization"] = f"Bearer {bearer}"
        return headers
