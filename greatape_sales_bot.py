# -*- coding: utf-8 -*-
"""
MIT License

Copyright (c) 2021 Dinesh Pinto

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import json
import logging
import sys
import time

import requests
from pycoingecko import CoinGeckoAPI

from discord_chibi_dinos_webhook import DiscordWebhookAPI
from twitter_bot import TwitterAPI

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)


class GreatApesSalesBot:
    def __init__(self, connect_twitter=False, connect_discord=False, discord_group=False):
        self.asset_limit = 10
        self.asset_contract_address = "0xA0F38233688bB578c0a88102A95b846c18bc0bA7"
        self.connect_twitter = connect_twitter
        self.connect_discord = connect_discord
        self.cg = CoinGeckoAPI()

        if self.connect_twitter:
            self.twitter_bot = TwitterAPI()
        elif self.connect_discord:
            self.discord_bot = DiscordWebhookAPI(group=discord_group)

        self.base_url = "https://api.opensea.io/api/v1/"

    def get_eth_usd_price(self) -> float:
        coin_id = "ethereum"
        vs_currency = "usd"
        return float(self.cg.get_price(ids=coin_id, vs_currencies=vs_currency)[coin_id][vs_currency])

    def request_last_sales(self) -> list:
        return self.parse_successful_event_data(self.get_successful_event_data())

    def get_successful_event_data(self) -> dict:
        url = self.base_url + "events"
        querystring = {
            "only_opensea": "true",
            "offset": "0",
            "limit": str(self.asset_limit),
            "asset_contract_address": self.asset_contract_address,
            "event_type": "successful"
        }
        response = requests.request("GET", url, headers={"Accept": "application/json"}, params=querystring)

        return json.loads(response.text)

    def get_asset_data(self, offset: int = 0, limit: int = 50):
        url = self.base_url + "assets"

        querystring = {
            "offset": str(offset),
            "limit": str(limit),
            "asset_contract_address": self.asset_contract_address,
        }
        response = requests.request("GET", url, headers={"Accept": "application/json"}, params=querystring)
        return json.loads(response.text)

    def get_event_data(self, offset: int = 0, limit: int = 50):
        url = self.base_url + "events"

        querystring = {
            "only_opensea": "true",
            "offset": str(offset),
            "limit": str(limit),
            "asset_contract_address": self.asset_contract_address,
        }
        response = requests.request("GET", url, headers={"Accept": "application/json"}, params=querystring)
        return json.loads(response.text)

    def parse_successful_event_data(self, json_dump: dict) -> list:
        json_list = []
        # Loop through the last sales
        for i in range(self.asset_limit):
            # json only contains the last sale info
            bundle_info = json_dump['asset_events'][i]['asset_bundle']
            asset_info = json_dump['asset_events'][i]['asset']

            if asset_info:
                is_bundle = False
                bundle_size = 0
                image_url = asset_info['image_url']
                great_ape_number = asset_info['name']
                product_link = asset_info['permalink']

                # Seller info
                seller_info = json_dump['asset_events'][i]['seller']
                if not seller_info['user']:
                    seller_username = None
                else:
                    seller_username = seller_info['user']['username']
                seller_address = seller_info['address']

                # Buyer info
                buyer_info = json_dump['asset_events'][i]['winner_account']
                if not buyer_info['user']:
                    buyer_username = None
                else:
                    buyer_username = buyer_info['user']['username']
                buyer_address = buyer_info['address']

                payment_info = json_dump['asset_events'][i]['payment_token']
                payment_token = payment_info['symbol']

                sale_id = json_dump['asset_events'][i]['id']
                if payment_token in ["ETH", "WETH"]:
                    sale_price = int(json_dump['asset_events'][i]['total_price']) / 1e18
                    try:
                        sale_price_usd = self.get_eth_usd_price() * sale_price
                    except Exception as exc:
                        logger.error(f"Exception: {exc}")
                        sale_price_usd = None
                else:
                    sale_price = float(json_dump['asset_events'][i]['total_price'])
                    sale_price_usd = None
            elif bundle_info:
                is_bundle = True
                great_ape_number = None
                bundle_size = len(bundle_info["assets"])

                image_url = bundle_info["assets"][0]["image_url"]
                product_link = bundle_info['permalink']

                # Seller info
                seller_info = json_dump['asset_events'][i]['seller']
                if not seller_info['user']:
                    seller_username = None
                else:
                    seller_username = seller_info['user']['username']
                seller_address = seller_info['address']

                # Buyer info
                buyer_info = json_dump['asset_events'][i]['winner_account']
                if not buyer_info['user']:
                    buyer_username = None
                else:
                    buyer_username = buyer_info['user']['username']
                buyer_address = buyer_info['address']

                payment_info = json_dump['asset_events'][i]['payment_token']
                payment_token = payment_info['symbol']

                sale_id = json_dump['asset_events'][i]['id']
                if payment_token in ["ETH", "WETH"]:
                    sale_price = int(json_dump['asset_events'][i]['total_price']) / 1e18
                    try:
                        sale_price_usd = self.get_eth_usd_price() * sale_price
                    except Exception as exc:
                        logger.error(f"Exception: {exc}")
                        sale_price_usd = None
                else:
                    sale_price = float(json_dump['asset_events'][i]['total_price'])
                    sale_price_usd = None
            else:
                logger.error("Neither asset nor bundle")
                continue

            json_info = {
                'bundle': is_bundle,
                'bundle_size': bundle_size,
                'asset_info': {
                    'asset_name': great_ape_number,
                    'asset_image': image_url,
                    'asset_link': product_link,
                },
                'seller_info': {
                    'seller_username': seller_username,
                    'seller_address': seller_address
                },
                'buyer_info': {
                    'buyer_username': buyer_username,
                    'buyer_address': buyer_address
                },
                'payment_token': payment_token,
                'sale_price': sale_price,
                'sale_price_usd': sale_price_usd,
                'sale_id': sale_id
            }
            json_list.append(json_info)

        return json_list

    @staticmethod
    def get_sales_ids(sales_list: list):
        sales_ids = []

        for sale in sales_list:
            sales_ids.append(sale["sale_id"])

        return sales_ids

    def start(self):
        old_sales_list = self.request_last_sales()
        old_sales_ids = self.get_sales_ids(old_sales_list)

        while True:
            try:
                new_sales_list = self.request_last_sales()
                new_sale_ids = self.get_sales_ids(new_sales_list)
            except Exception as exc:
                new_sales_list = old_sales_list
                new_sale_ids = []
                logger.error(f'Exception: {exc}')

            recent_sale_ids = list(set(new_sale_ids) - set(old_sales_ids))

            if recent_sale_ids:
                for idx in range(len(recent_sale_ids)):
                    logger.info(f"New sale, ID={recent_sale_ids[idx]}")

                    for new_sale in new_sales_list:
                        if new_sale["sale_id"] == recent_sale_ids[idx]:
                            if self.connect_twitter:
                                try:
                                    self.twitter_bot.tweet_with_media(new_sale)
                                except Exception as exc:
                                    logger.error(f"Twitter Exception (ID={recent_sale_ids[idx]}): {exc}")
                            if self.connect_discord:
                                try:
                                    self.discord_bot.send_webhook(new_sale)
                                except Exception as exc:
                                    logger.error(f"Discord Exception (ID={recent_sale_ids[idx]}): {exc}")
            else:
                logger.info('No new sales')

            old_sales_ids = new_sale_ids
            old_sales_list = new_sales_list

            time.sleep(60)


if __name__ == "__main__":
    gas_bot = GreatApesSalesBot(connect_twitter=False, connect_discord=True, discord_group=True)
    gas_bot.start()
