Examples
==========
This is a collection of examples that demonstrate how to use the library. If you have an that helped you, please share!

Logging In
----------

.. code-block:: python

    from public_invest_api import Public

    public = Public()
    public.login(
        username='your_email',
        password='your_password',
        wait_for_2fa=True # When logging in for the first time, you need to wait for the SMS code
    )

This will ask for the 2FA code sent to your phone via sms. It wil display an `input()` promopt in the terminal.

If you'd like to log in using environment variables (for added account credentials protection), you can set the following environment variables (this is done on Mac with zsh-based terminal):

.. code-block:: bash

    export PUBLIC_USERNAME='<email associated with your Public account>'
    export PUBLIC_PSWD='<password associated with your Public account>'

Then you can log in without passing any arguments:

.. code-block:: python

    from public_invest_api import Public
    import os

    public = Public()
    public.login(
        username=os.getenv('PUBLIC_USERNAME'),
        password=os.getenv('PUBLIC_PSWD'),
        wait_for_2fa=True
    )

If you'd like to handle the 2FA code yourself programmatically, set `wait_for_2fa=False` and the function will throw an Exception relating to 2FA. 
Catch this, then when you get the 2FA code, call it again with these arguments:

.. code-block:: python

    public.login(
        username='your_email',
        password='your_password',
        wait_for_2fa=False,
        code='your_2fa_code' # Should be six digit integer
    )

Get Stock Holdings
------------------

.. code-block:: python

    positions = public.get_positions()
    for position in positions:
        print(position)

Placing Orders
--------------

.. code-block:: python

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

These aren't all of the functions available, but are some of the most common ones. For a full list of functions, see the :ref:`Functions` section.
