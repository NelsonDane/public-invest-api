# Unofficial Public.com Invest API

This is an unofficial API for Public.com. It is a simple Python wrapper around the Public.com requests API. It is not affiliated with Public.com in any way. Use at your own risk.

This is still a very work in progress, so it will have bugs and missing features. Feel free to contribute!

## Installation

```bash
pip install public-invest-api
```

## Usage: Logging In

```python
from public_invest_api import Public

public = Public()
public.login(
    username='your_email',
    password='your_password',
    wait_for_2fa=True # When logging in for the first time, you need to wait for the SMS code
)
```

If you'd like to handle the 2FA code yourself, set `wait_for_2fa=False` and it will throw an Exception relating to 2FA. Catch this, then when you get the 2FA code, call it again with the code:

```python
public.login(
    username='your_email',
    password='your_password',
    wait_for_2fa=False,
    code='your_2fa_code' # Should be six digit integer
)
```

## Usage: Get Holdings

```python
positions = public.get_positions()
for position in positions:
    print(position)
```

## Usage: Placing Orders

```python
order = public.place_order(
    symbol='AAPL',
    quantity=1,
    side='BUY', # or 'SELL'
    order_type='MARKET', # or 'LIMIT' or 'STOP'
    limit_price=None # pass float if using 'LIMIT' order_type
    time_in_force='DAY', # or 'GTC' or 'IOC' or 'FOK'
    is_dry_run=False, # If True, it will not actually place the order
    tip=0 # The amount to tip Public.com
)
print(order)
```

## Contributing
Found or fixed a bug? Have a feature request? Feel free to open an issue or pull request!

Enjoying the project? Feel free to Sponsor me on GitHub or Ko-fi!

[![Sponsor](https://img.shields.io/badge/sponsor-30363D?style=for-the-badge&logo=GitHub-Sponsors&logoColor=#white)](https://github.com/sponsors/NelsonDane)
[![ko-fi](https://img.shields.io/badge/Ko--fi-F16061?style=for-the-badge&logo=ko-fi&logoColor=white
)](https://ko-fi.com/X8X6LFCI0)

## DISCLAIMER
DISCLAIMER: I am not a financial advisor and not affiliated with Public.com. Use this tool at your own risk. I am not responsible for any losses or damages you may incur by using this project. This tool is provided as-is with no warranty.
