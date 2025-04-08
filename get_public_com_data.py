from public_invest_api import Public
import os

public = Public()

public.login(
    username=os.getenv('PUBLIC_USERNAME'),
    password=os.getenv('PUBLIC_PSWD'),
    wait_for_2fa=True # When logging in for the first time, you need to wait for the SMS code
)


# pending_deposit = public.get_account_history(date = 'current_month', 
#                            asset_class = 'all', 
#                            min_amount = None, 
#                            max_amount = None, 
#                            transaction_type = 'deposit', 
#                            status = 'pending')

current_month_buy = public.get_account_history(date = 'current_month', 
                           asset_class = 'all', 
                           min_amount = None, 
                           max_amount = None, 
                           transaction_type = 'buy', 
                           status = 'completed')


print(current_month_buy)
# print(current_month_buy['transactions'][0]['payload']['amount'])