import configparser

from postgrest import exceptions
from supabase import Client, create_client


class Supa:
    def __init__(self, admin=False) -> None:
        config = configparser.ConfigParser()
        config.read('./config.cfg')
        self.supabase_config = config['supabase']
        if (admin == True):
            self.supabase_client = create_client(
                self.supabase_config['base_url'], self.supabase_config['service_role'])

        else:
            self.supabase_client: Client = create_client(
                self.supabase_config['base_url'], self.supabase_config['anon_key'])

    def list_all_users(self):
        result = self.supabase_client.auth.admin.list_users()
        return result

    def sign_user_out(self):
        result = self.supabase_client.auth.sign_out()
        return result

    def sign_user_up(self, email: str, password: str):
        result = self.supabase_client.auth.sign_up({
            "email": f"{email}",
            "password": f"{password}"
        })
        return result

    def sign_user_in(self, email: str, password: str):
        result = self.supabase_client.auth.sign_in_with_password({
            "email": f"{email}",
            "password": f"{password}"
        })
        return result

    def create_users_funds(self, user_id: str):
        try:
            data = self.supabase_client.table("funds_table").insert({
                "user_id": f"{user_id}",
            }).execute()
        except exceptions.APIError:
            data = {"funds": "already exists"}

        return data

    def fetch_funds(self, user_id: str):
        data = self.supabase_client.table("funds_table").select(
            "funds").eq('user_id', f'{user_id}').execute()
        return data

    def set_funds(self, user_id: str, new_funds: float):
        data = self.supabase_client.table("funds_table").update({
            "funds": f'{new_funds}',
        }).eq("user_id", user_id).execute()
        return data

    def operation_insertion(self, user_id: str, stock_name: str, operation: str, quantity: int, bought_at: float, admin_overide=False):
        return_value = {}
        held_stocks = self.fetch_held_stocks(user_id)
        data = self.fetch_funds(user_id)
        insert = True
        if (operation == "buy"):
            value = quantity * bought_at
            current_funds = data.data[0]['funds']
            try:
                if (held_stocks[stock_name] < 0):
                    print("SHORT BUY")
                    normal_buy = held_stocks[stock_name] + quantity
                    short_buy = abs(held_stocks[stock_name])
                    current_funds -= (normal_buy * bought_at)
                    print("FUNDS AFTER NORMAL BUY", current_funds)
                    current_funds -= (short_buy * bought_at)
                    print("FUNDS AFTER SHORT BUY", current_funds)
                    if (not admin_overide):
                        response = self.set_funds(user_id, current_funds)
                        return_value['funds'] = response.data[0]['funds']
                        insert = True
                    else:
                        return_value['funds'] = current_funds
                elif (current_funds >= value):
                    print("COMPLETE NORMAL BUY")
                    current_funds -= value
                    print("FUNDS AFTER COMPLETE NORMAL BUY", current_funds)
                    if (not admin_overide):
                        response = self.set_funds(user_id, current_funds)
                # print(response.data[0]['funds'])
                        return_value['funds'] = response.data[0]['funds']
                        insert = True
                    else:
                        return_value['funds'] = current_funds

                elif (current_funds < value):
                    return_value = {'error': 'INSUFFICIENT FUNDS'}
                    insert = False

            except KeyError:
                if (current_funds >= value):
                    print("COMPLETE NORMAL BUY")
                    current_funds -= value
                    print("FUNDS AFTER COMPLETE NORMAL BUY", current_funds)
                    if (not admin_overide):
                        response = self.set_funds(user_id, current_funds)
                # print(response.data[0]['funds'])
                        return_value['funds'] = response.data[0]['funds']
                        insert = True
                    else:
                        return_value['funds'] = current_funds
                elif (current_funds < value):
                    return_value = {'error': 'INSUFFICIENT FUNDS'}
                    insert = False

        if (operation == "sell"):
            insert = True
            try:
                if (quantity > held_stocks[stock_name]):
                    print("SHORT SELL")
                    short_sell = quantity - held_stocks[stock_name]
                    short_value = short_sell * bought_at
                    if (short_value <= data.data[0]['funds']):
                        normal_sell = held_stocks[stock_name]
                        value = normal_sell * bought_at
                        current_funds = data.data[0]['funds']
                        current_funds += value
                        print("FUNDS AFTER NORMAL SELL", current_funds)
                        current_funds += short_value
                        if(current_funds < 2000000):
                            print("FUNDS AFTER SHORT_SELL", current_funds)
                            if (not admin_overide):
                                response = self.set_funds(user_id, current_funds)
                                return_value['funds'] = response.data[0]['funds']
                                insert = True
                        # return_value = {'error': 'Selling more than you own'}
                        # insert = False
                            else:
                                return_value['funds'] = current_funds
                        else:
                            return_value['funds'] = current_funds

                    else:
                        return_value = {'error': 'INSUFFICIENT FUNDS'}
                        insert = False
                else:
                    print("NORMAL SELL")
                    value = quantity * bought_at
                    current_funds = data.data[0]['funds']
                    current_funds += value
                    print("FUNDS AFTER NORMAL SELL", current_funds)
                    if (not admin_overide):
                        response = self.set_funds(user_id, current_funds)
                        return_value['funds'] = response.data[0]['funds']
                        insert = True
                    else:
                        return_value['funds'] = current_funds

            except KeyError:
                # return_value = {'error': "You don't own any of this companies stock"}
                print("SHORT SELL WHEN YOU HAVE 0 QUANTITY")
                short_sell = quantity
                short_value = short_sell * bought_at
                if (short_value <= data.data[0]['funds']):
                    current_funds = data.data[0]['funds']
                    current_funds -= short_value
                    print("FUNDS AFTER SHORT SELL", current_funds)
                    if (not admin_overide):
                        response = self.set_funds(user_id, current_funds)
                        return_value['funds'] = response.data[0]['funds']
                        insert = True
                    else:
                        return_value['funds'] = current_funds
                else:
                    return_value = {'error': 'INSUFFICIENT FUNDS'}
                    insert = False
        if (insert == True and not admin_overide):
            try:
                quantity_before_buying = held_stocks[stock_name]
            except KeyError:
                quantity_before_buying = 0
            data = self.supabase_client.table("main_ops_table").insert({
                "user_id": f"{user_id}",
                "stock_name": f"{stock_name}",
                "operation": f"{operation}",
                "quantity": f"{quantity}",
                "bought_at": f"{bought_at}",
                "quantity_before_buying": f"{quantity_before_buying}"
            }).execute()
        else:
            data = "empty"

        return {'data': data, 'response': return_value}

    def fetch_held_stocks(self, user_id: str):
        return_value = {}
        bought_at = []
        buy = self.supabase_client.table("main_ops_table").select("stock_name", "quantity").eq("user_id", f"{user_id}").eq(
            "operation", "buy").eq("user_id", f"{user_id}").eq("operation", "buy").execute()
        sell = self.supabase_client.table("main_ops_table").select("stock_name", "quantity").eq(
            "user_id", f"{user_id}").eq("operation", "sell").execute()

        all_ops = self.supabase_client.table("main_ops_table").select(
            "stock_name", "quantity", "bought_at", "operation").eq("user_id", f"{user_id}").execute()

        total_buy = 0
        total_sell = 0
        if (len(buy.data) != 0):
            for buy_value in buy.data:
                if (buy_value["stock_name"] in return_value):
                    return_value[buy_value["stock_name"]
                                 ] += buy_value["quantity"]
                else:
                    return_value[buy_value["stock_name"]
                                 ] = buy_value["quantity"]
                total_buy += buy_value["quantity"]
        if (len(sell.data) != 0):
            for sell_value in sell.data:
                if (sell_value["stock_name"] in return_value):
                    return_value[sell_value["stock_name"]
                                 ] -= sell_value["quantity"]
                else:
                    return_value[sell_value["stock_name"]
                                 ] = -(sell_value["quantity"])
                total_sell += sell_value["quantity"]
        temp = {}
        for all_vals in all_ops.data:
            temp["stock_name"] = all_vals["stock_name"]
            temp["quantity"] = all_vals["quantity"]
            temp["bought_at"] = all_vals["bought_at"]
            temp["operation"] = all_vals["operation"]
            bought_at.append(temp)
            temp = {}

        return_value['total_quantity'] = total_buy - total_sell
        return_value["history"] = bought_at
        # print(len(sell.data)) = 0 if empty
        return return_value
