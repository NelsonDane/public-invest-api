class InvalidAccessTokenError(Exception):
    """Exception raised when a token results in an invalid or blank response."""

    def __init__(self) -> None:
        """Initialize InvalidAccessTokenError Exception."""
        self.message = "Invalid access token. Please check that your token is valid."
        super().__init__(self.message)


class PublicAPIError(Exception):
    """Exception raised when an API request does not return 200."""

    def __init__(self, msg: str) -> None:
        """Initialize PublicAPIError Exception."""
        super().__init__(msg)
