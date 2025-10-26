import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from functools import wraps
from typing import Concatenate, ParamSpec, TypeVar
from zoneinfo import ZoneInfo, available_timezones

import requests

from public_invest_api.endpoints import Endpoints
from public_invest_api.models.com.hellopublic.userapigateway.api.rest import account, history, order, portfolio, preflight
from public_invest_api.models.com.hellopublic.userapigateway.api.rest.marketdata import quote
from public_invest_api.utils import InvalidAccessTokenError, PublicAPIError

P = ParamSpec("P")
R = TypeVar("R")


def _refresh_check(func: Callable[Concatenate["Public", P], R]) -> Callable[Concatenate["Public", P], R]:
    """Check if the access token is expired and refresh it if necessary.

    Args:
        func: The function to wrap.

    Returns:
        The wrapped function.

    """

    @wraps(func)
    def wrapper(self: "Public", *args: P.args, **kwargs: P.kwargs) -> R:
        if self.expires_at and datetime.now(tz=self.timezone) >= self.expires_at:
            self._refresh_jwt_access_token()
        return func(self, *args, **kwargs)  # type: ignore  # noqa: PGH003

    return wrapper


class Public:
    """Object to interact with the Public Invest API. One object per account/token."""

    def __init__(self, api_access_token: str, minutes_valid: int = 15, timezone: str = "America/New_York") -> None:
        """Initialize the Public.com API client.

        Args:
            api_access_token: The API access token to use for authentication.
            minutes_valid: The number of minutes the JWT access token is valid for. Defaults to 15.
            timezone: The timezone to use for the API requests. Defaults to None, which uses the system timezone.

        Raises:
            ValueError: If the provided timezone is not valid.
            InvalidAccessTokenError: If the provided API access token is not valid.

        """
        if timezone not in available_timezones():
            msg = f"Invalid timezone: {timezone}. Available timezones: {available_timezones()}"
            raise ValueError(msg)
        self.session = requests.Session()
        self.endpoints = Endpoints()
        self.api_access_token = api_access_token
        self.session.headers.update(self.endpoints.build_headers())
        self.timeout = 10
        self.timezone = ZoneInfo(timezone)
        self.minutes_valid = minutes_valid
        try:
            self._refresh_jwt_access_token()
        except PublicAPIError as e:
            raise InvalidAccessTokenError from e

    def _refresh_jwt_access_token(self) -> None:
        """Get a JWT access token by making a POST request to the JWT URL. https://public.com/api/docs/resources/authorization/create-personal-access-token.

        Raises:
            PublicAPIError: If the JWT request fails (doesn't return 200).

        """
        request_body = {
            "validityInMinutes": self.minutes_valid,
            "secret": self.api_access_token,
        }
        response = self.session.post(
            url=self.endpoints.jwt_url(),
            headers=self.session.headers,
            json=request_body,
            timeout=self.timeout,
        )
        if not response.ok:
            msg = f"Access Token (JWT) failed with status code {response.status_code}: {response.text}"
            raise PublicAPIError(msg)
        response = response.json()
        # Update session headers with new bearer token
        self.session.headers.update(self.endpoints.build_headers(bearer=response["accessToken"]))  # type: ignore[index]
        self.expires_at = datetime.now(tz=self.timezone) + timedelta(minutes=self.minutes_valid)

    @_refresh_check
    def get_accounts(self) -> list[account.AccountSettings]:
        """Retrieve financial accounts associated with the user. https://public.com/api/docs/resources/list-accounts/get-accounts.

        Returns:
            AccountSettings: The account settings for the user.

        Raises:
            PublicAPIError: If the accounts request fails (doesn't return 200).

        """
        response = self.session.get(url=self.endpoints.get_accounts_url(), headers=self.session.headers, timeout=self.timeout)
        if not response.ok:
            msg = f"Failed to retrieve accounts: {response.status_code} {response.text}"
            raise PublicAPIError(msg)
        return account.AccountSettingsResponse(**response.json()).accounts or []

    @_refresh_check
    def get_portfolio(self, account_id: str) -> portfolio.GatewayPortfolioAccountV2:
        """Retrieve the portfolio for a specific account. https://public.com/api/docs/resources/account-details/get-account-portfolio-v2.

        Args:
            account_id: The unique identifier for the user's account.

        Returns:
            GatewayPortfolioAccountV2: The portfolio information for the specified account.

        Raises:
            PublicAPIError: If the portfolio request fails (doesn't return 200).

        """
        response = self.session.get(url=self.endpoints.get_account_portfolio_v2_url(account_id), headers=self.session.headers, timeout=self.timeout)
        if not response.ok:
            msg = f"Failed to retrieve portfolio: {response.status_code} {response.text}"
            raise PublicAPIError(msg)
        return portfolio.GatewayPortfolioAccountV2(**response.json())

    @_refresh_check
    def get_history(
        self,
        account_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page_size: int | None = None,
        next_token: str | None = None,
    ) -> history.GatewayHistoryResponsePage:
        """Retrieve the account history for a specific account. https://public.com/api/docs/resources/account-details/get-history.

        Args:
            account_id: The unique identifier for the user's account.
            start_date: The start date for the history query. If None, no start date is applied.
            end_date: The end date for the history query. If None, no end date is applied.
            page_size: The number of results to return per page. If None, the default page size is used.
            next_token: The token for the next page of results. If None, the first page is retrieved.

        Returns:
            GatewayHistoryResponsePage: The account history information for the specified account.

        Raises:
            PublicAPIError: If the history request fails (doesn't return 200).

        """
        params = {}
        # Dates in ISO 8601 format with timezone
        if start_date is not None:
            params["start"] = start_date.astimezone(self.timezone).isoformat()
        if end_date is not None:
            params["end"] = end_date.astimezone(self.timezone).isoformat()
        if page_size is not None:
            params["page_size"] = str(page_size)
        if next_token is not None:
            params["next_token"] = next_token
        if params != {}:
            self.session.params = params
        response = self.session.get(url=self.endpoints.get_history_url(account_id), headers=self.session.headers, timeout=self.timeout)
        if not response.ok:
            msg = f"Failed to retrieve account history: {response.status_code} {response.text}"
            raise PublicAPIError(msg)
        return history.GatewayHistoryResponsePage(**response.json())

    @_refresh_check
    def get_all_instruments(
        self,
        type_filter: list[history.SecurityType] | None = None,
        trading_filter: list[order.Trading] | None = None,
        fractional_trading_filter: list[order.FractionalTrading] | None = None,
        option_trading_filter: list[order.OptionTrading] | None = None,
        option_spread_trading_filter: list[order.OptionSpreadTrading] | None = None,
    ) -> list[order.ApiInstrumentDto]:
        """Get all instruments available to the user. https://public.com/api/docs/resources/instrument-details/get-all-instruments.

        Args:
            type_filter: List of security types to filter by.
            trading_filter: List of trading types to filter by.
            fractional_trading_filter: List of fractional trading types to filter by.
            option_trading_filter: List of option trading types to filter by.
            option_spread_trading_filter: List of option spread trading types to filter by.

        Returns:
            The JSON response from the all instruments URL containing the user's instruments.

        Raises:
            PublicAPIError: If the all instruments request fails (i.e., response status code is not 200).

        """
        params = {}
        if type_filter:
            params["typeFilter"] = ",".join([t.value for t in type_filter])
        if trading_filter:
            params["tradingFilter"] = ",".join([t.value for t in trading_filter])
        if fractional_trading_filter:
            params["fractionalTradingFilter"] = ",".join([t.value for t in fractional_trading_filter])
        if option_trading_filter:
            params["optionTradingFilter"] = ",".join([t.value for t in option_trading_filter])
        if option_spread_trading_filter:
            params["optionSpreadTradingFilter"] = ",".join([t.value for t in option_spread_trading_filter])
        response = self.session.get(
            url=self.endpoints.get_all_instruments_url(),
            headers=self.session.headers,
            params=params,
            timeout=self.timeout,
        )
        if not response.ok:
            msg = f"All instruments request failed with status code {response.status_code}: {response.text}"
            raise PublicAPIError(msg)
        return order.ApiInstrumentResponse(**response.json()).instruments or []

    def get_instrument(self, symbol: str, symbol_type: order.Type) -> order.ApiInstrumentDto:
        """Get a specific instrument by symbol and type.

        Args:
            symbol: The stock symbol to get the instrument for.
            symbol_type: The type of the stock symbol.

        Returns:
            The instrument matching the symbol and type.

        Raises:
            PublicAPIError: If the instrument request fails (i.e., response status code is not 200).

        """
        response = self.session.get(
            url=self.endpoints.get_instrument_url(symbol, symbol_type.value),
            headers=self.session.headers,
            timeout=self.timeout,
        )
        if not response.ok:
            msg = f"Failed to retrieve instrument {symbol}: {response.status_code} {response.text}"
            raise PublicAPIError(msg)
        return order.ApiInstrumentDto(**response.json())

    @_refresh_check
    def get_quotes(self, account_id: str, instruments: list[order.GatewayOrderInstrument]) -> list[quote.GatewayQuote]:
        """Get quotes for the given instruments. https://public.com/api/docs/resources/market-data/get-quotes.

        Args:
            account_id: The unique identifier for the user's account.
            instruments: List of instruments to query quotes.

        Returns:
            A GatewayQuoteResponse object containing the quotes for the specified instruments.

        Raises:
            PublicAPIError: If the quotes request fails (i.e., response status code is not 200).

        """
        response = self.session.post(
            url=self.endpoints.get_quotes_url(account_id=account_id),
            headers=self.session.headers,
            json=quote.GatewayQuoteRequest(instruments=instruments).model_dump(),
            timeout=self.timeout,
        )
        if not response.ok:
            msg = f"Failed to retrieve quotes for account {account_id}: {response.status_code} {response.text}"
            raise PublicAPIError(msg)
        return quote.GatewayQuoteResponse(**response.json()).quotes or []

    @_refresh_check
    def get_option_expirations(self, account_id: str, instrument: order.GatewayOrderInstrument) -> quote.GatewayOptionExpirationsResponse:
        """Get option expirations for a given instrument. https://public.com/api/docs/resources/market-data/get-option-expirations.

        Args:
            account_id: The unique identifier for the user's account.
            instrument: The instrument to get option expirations for.

        Returns:
            A GatewayOptionExpirationsResponse object containing the option expirations for the specified instrument.

        Raises:
            PublicAPIError: If the option expirations request fails (i.e., response status code is not 200).

        """
        response = self.session.post(
            url=self.endpoints.get_options_expirations_url(account_id=account_id),
            headers=self.session.headers,
            json=quote.GatewayOptionExpirationsRequest(instrument=instrument).model_dump(),
            timeout=self.timeout,
        )
        if not response.ok:
            msg = f"Failed to retrieve option expirations for account {account_id}: {response.status_code} {response.text}"
            raise PublicAPIError(msg)
        return quote.GatewayOptionExpirationsResponse(**response.json())

    @_refresh_check
    def get_option_chain(self, account_id: str, instrument: order.GatewayOrderInstrument, expiration_date: datetime) -> quote.GatewayOptionChainResponse:
        """Get option chain for a given instrument and expiration date. https://public.com/api/docs/resources/market-data/get-option-chain.

        Args:
            account_id: The unique identifier for the user's account.
            instrument: The instrument to get the option chain for.
            expiration_date: The expiration date of the option chain.

        Returns:
            A GatewayOptionChainResponse object containing the option chain for the specified instrument and expiration date.

        Raises:
            PublicAPIError: If the option chain request fails (i.e., response status code is not 200).

        """
        response = self.session.post(
            url=self.endpoints.get_options_chain_url(account_id=account_id),
            headers=self.session.headers,
            json=quote.GatewayOptionChainRequest(instrument=instrument, expirationDate=expiration_date).model_dump(),
            timeout=self.timeout,
        )
        if not response.ok:
            msg = f"Failed to retrieve option chain for account {account_id}: {response.status_code} {response.text}"
            raise PublicAPIError(msg)
        return quote.GatewayOptionChainResponse(**response.json())

    @_refresh_check
    def preflight_single_leg(  # noqa: PLR0913, PLR0917
        self,
        account_id: str,
        instrument: order.GatewayOrderInstrument,
        order_side: preflight.OrderSide,
        order_type: preflight.OrderType,
        expiration: order.OrderExpiration,
        quantity: str | None = None,
        amount: str | None = None,
        limit_price: str | None = None,
        stop_price: str | None = None,
        open_close_indicator: preflight.OpenCloseIndicator | None = None,
    ) -> preflight.PreflightSingleLegResponse:
        """Preflight a single leg order. https://public.com/api/docs/resources/order-placement/preflight-single-leg.

        Args:
            account_id: The unique identifier for the user's account.
            instrument: The instrument to preflight the order for.
            order_side: The side of the order (BUY/SELL).
            order_type: The type of the order (MARKET/LIMIT/STOP/STOP_LIMIT).
            expiration: The expiration of the order.
            quantity: The quantity of the order. Mutually exclusive with `amount`.
            amount: The amount of the order. Mutually exclusive with `quantity`.
            limit_price: The limit price of the order. Used when order_type is LIMIT or STOP_LIMIT.
            stop_price: The stop price of the order. Used when order_type is STOP or STOP_LIMIT.
            open_close_indicator: The open/close indicator for options orders.

        Returns:
            A PreflightSingleLegResponse object containing the preflight information for the specified order.

        Raises:
            PublicAPIError: If the preflight request fails (i.e., response status code is not 200).

        """
        response = self.session.post(
            url=self.endpoints.preflight_single_leg_url(account_id=account_id),
            headers=self.session.headers,
            json=preflight.PreflightSingleLegRequest(
                instrument=instrument,
                orderSide=order_side,
                orderType=order_type,
                expiration=expiration,
                quantity=quantity,
                amount=amount,
                limitPrice=limit_price,
                stopPrice=stop_price,
                openCloseIndicator=open_close_indicator,
            ).model_dump(),
            timeout=self.timeout,
        )
        if not response.ok:
            msg = f"Failed to preflight single leg for account {account_id}: {response.status_code} {response.text}"
            raise PublicAPIError(msg)
        return preflight.PreflightSingleLegResponse(**response.json())

    @_refresh_check
    def preflight_multi_leg(  # noqa: PLR0913, PLR0917
        self,
        account_id: str,
        order_type: preflight.OrderType,
        expiration: order.OrderExpiration,
        legs: list[order.GatewayOrderLeg],
        limit_price: str,
        quantity: str | None = None,
    ) -> preflight.PreflightMultiLegResponse:
        """Preflight a multi leg order. https://public.com/api/docs/resources/order-placement/preflight-multi-leg.

        Args:
            account_id: The unique identifier for the user's account.
            order_type: The type of the order (MARKET/LIMIT/STOP/STOP_LIMIT).
            expiration: The expiration of the order.
            quantity: The quantity of the order.
            limit_price: The limit price of the order. Used when order_type is LIMIT or STOP_LIMIT.
            legs: The legs of the multi leg order.

        Returns:
            A PreflightMultiLegResponse object containing the preflight information for the specified order.

        Raises:
            PublicAPIError: If the preflight request fails (i.e., response status code is not 200).

        """
        response = self.session.post(
            url=self.endpoints.preflight_multi_leg_url(account_id=account_id),
            headers=self.session.headers,
            json=preflight.PreflightMultiLegRequest(
                orderType=order_type,
                expiration=expiration,
                quantity=quantity,
                limitPrice=limit_price,
                legs=legs,
            ).model_dump(),
            timeout=self.timeout,
        )
        if not response.ok:
            msg = f"Failed to preflight multi leg for account {account_id}: {response.status_code} {response.text}"
            raise PublicAPIError(msg)
        return preflight.PreflightMultiLegResponse(**response.json())

    @_refresh_check
    def place_order(  # noqa: PLR0913, PLR0917
        self,
        account_id: str,
        instrument: order.GatewayOrderInstrument,
        order_side: order.OrderSide,
        order_type: order.OrderType,
        expiration: order.OrderExpiration,
        quantity: str | None = None,
        amount: str | None = None,
        limit_price: str | None = None,
        stop_price: str | None = None,
        open_close_indicator: order.OpenCloseIndicator | None = None,
    ) -> order.ApiOrderResult:
        """Place an order. https://public.com/api/docs/resources/order-placement/place-order.

        Args:
            account_id: The unique identifier for the user's account.
            instrument: The instrument to place the order for.
            order_side: The side of the order (BUY/SELL).
            order_type: The type of the order (MARKET/LIMIT/STOP/STOP_LIMIT).
            expiration: The expiration of the order.
            quantity: The quantity of the order. Mutually exclusive with `amount`.
            amount: The amount of the order. Mutually exclusive with `quantity`.
            limit_price: The limit price of the order. Used when order_type is LIMIT or STOP_LIMIT.
            stop_price: The stop price of the order. Used when order_type is STOP or STOP_LIMIT.
            open_close_indicator: The open/close indicator for options orders.

        Returns:
            An ApiOrderResult object containing the result of the placed order.

        Raises:
            PublicAPIError: If the place order request fails (i.e., response status code is not 200).

        """
        response = self.session.post(
            url=self.endpoints.place_order_url(account_id=account_id),
            headers=self.session.headers,
            json=order.ApiOrderRequest(
                orderId=uuid.uuid4(),
                instrument=instrument,
                orderSide=order_side,
                orderType=order_type,
                expiration=expiration,
                quantity=quantity,
                amount=amount,
                limitPrice=limit_price,
                stopPrice=stop_price,
                openCloseIndicator=open_close_indicator,
            ).model_dump(),
            timeout=self.timeout,
        )
        if not response.ok:
            msg = f"Failed to place order for account {account_id}: {response.status_code} {response.text}"
            raise PublicAPIError(msg)
        return order.ApiOrderResult(**response.json())

    @_refresh_check
    def place_multi_leg_order(
        self,
        account_id: str,
        quantity: int,
        limit_price: str,
        expiration: order.OrderExpiration,
        legs: list[order.GatewayOrderLeg],
    ) -> order.ApiOrderResult:
        """Place a multi leg order. https://public.com/api/docs/resources/order-placement/place-multileg-order.

        Args:
            account_id: The unique identifier for the user's account.
            expiration: The expiration of the order.
            quantity: The quantity of the order.
            limit_price: The limit price of the order. Used when order_type is LIMIT or STOP_LIMIT.
            legs: The legs of the multi leg order.

        Returns:
            An ApiOrderResult object containing the result of the placed order.

        Raises:
            PublicAPIError: If the place multi leg order request fails (i.e., response status code is not 200).

        """
        response = self.session.post(
            url=self.endpoints.place_multi_leg_order_url(account_id=account_id),
            headers=self.session.headers,
            json=order.ApiMultilegOrderRequest(
                orderId=uuid.uuid4(),
                type=order.TypeModel1.LIMIT,
                expiration=expiration,
                quantity=quantity,
                limitPrice=limit_price,
                legs=legs,
            ).model_dump(),
            timeout=self.timeout,
        )
        if not response.ok:
            msg = f"Failed to place multi leg order for account {account_id}: {response.status_code} {response.text}"
            raise PublicAPIError(msg)
        return order.ApiOrderResult(**response.json())

    @_refresh_check
    def get_order(self, account_id: str, order_id: uuid.UUID) -> order.GatewayOrder:
        """Retrieve the details of a specific order. https://public.com/api/docs/resources/order-placement/get-order.

        Args:
            account_id: The unique identifier for the user's account.
            order_id: The unique identifier for the order.

        Returns:
            A GatewayOrderDetails object containing the details of the specified order.

        Raises:
            PublicAPIError: If the get order request fails (i.e., response status code is not 200).

        """
        response = self.session.get(
            url=self.endpoints.get_order_url(account_id=account_id, order_id=str(order_id)),
            headers=self.session.headers,
            timeout=self.timeout,
        )
        if not response.ok:
            msg = f"Failed to retrieve order {order_id} for account {account_id}: {response.status_code} {response.text}"
            raise PublicAPIError(msg)
        return order.GatewayOrder(**response.json())

    @_refresh_check
    def cancel_order(self, account_id: str, order_id: uuid.UUID) -> None:
        """Cancel a specific order. https://public.com/api/docs/resources/order-placement/cancel-order.

        Args:
            account_id: The unique identifier for the user's account.
            order_id: The unique identifier for the order.

        Raises:
            PublicAPIError: If the cancel order request fails (i.e., response status code is not 200).

        """
        response = self.session.delete(
            url=self.endpoints.cancel_order_url(account_id=account_id, order_id=str(order_id)),
            headers=self.session.headers,
            timeout=self.timeout,
        )
        if not response.ok:
            msg = f"Failed to cancel order {order_id} for account {account_id}: {response.status_code} {response.text}"
            raise PublicAPIError(msg)
