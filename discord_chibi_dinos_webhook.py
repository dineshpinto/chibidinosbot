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
import locale
import logging
import sys

import requests

from config import DISCORD_WEBHOOK_PERSONAL, DISCORD_WEBHOOK_GAS

locale.setlocale(locale.LC_ALL, '')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)


class DiscordWebhookAPI:
    def __init__(self, group=False):
        if group:
            self.discord_webhook = DISCORD_WEBHOOK_GAS
            logger.info("Connected to group Discord Webhook")
        else:
            self.discord_webhook = DISCORD_WEBHOOK_PERSONAL
            logger.info("Connected to personal Discord Webhook")

    def test_webhook(self, text: str):
        json_info = json.dumps(
            {
                'embeds': [
                    {
                        'title': f"{text}"
                    }
                ]
            }
        )
        logger.info("Testing Discord Webhook...")
        requests.post(self.discord_webhook, data=json_info, headers={"Content-Type": "application/json"})
        logger.info(f"Posted successfully to Discord Webhook")

    def send_webhook(self, sale_data: dict):
        asset_info = sale_data['asset_info']
        seller_info = sale_data['seller_info']
        buyer_info = sale_data['buyer_info']
        payment_token = sale_data['payment_token']
        sale_price = sale_data['sale_price']

        # Format ETH addresses if usernames are not available
        addr_chars = 8
        if seller_info["seller_username"]:
            seller_name = seller_info['seller_username']
        else:
            seller_name = seller_info["seller_address"][:addr_chars]

        if buyer_info["buyer_username"]:
            buyer_name = buyer_info['buyer_username']
        else:
            buyer_name = buyer_info["buyer_address"][:addr_chars]

        if not sale_data["bundle"]:
            if sale_price == 0:
                title = f"{asset_info['asset_name']} was transferred!"
            else:
                title = f"{asset_info['asset_name']} was purchased!"
        else:
            if sale_price == 0:
                title = f"Great Ape Bundle of {sale_data['bundle_size']} was transferred!"
            else:
                title = f"Great Ape Bundle of {sale_data['bundle_size']} was purchased!"

        # Format sale price in USD
        if sale_data["sale_price_usd"]:
            sale_price_usd = f" ({locale.currency(sale_data['sale_price_usd'], grouping=True)}) "
        else:
            sale_price_usd = ""

        # Format json message
        json_info = json.dumps(
            {
                'embeds': [
                    {
                        'title': title,
                        'url': asset_info['asset_link'],
                        'fields': [
                            {
                                'name': '**Sale price**',
                                'value': f'{sale_price} {payment_token}{sale_price_usd}',
                                'inline': 'false'
                            },
                            {
                                'name': '**Buyer**',
                                'value': f"[{buyer_name}](https://opensea.io/{buyer_info['buyer_address']})",
                                'inline': 'true'
                            },
                            {
                                'name': '**Seller**',
                                'value': f"[{seller_name}](https://opensea.io/{seller_info['seller_address']})",
                                'inline': 'true'
                            }
                        ],
                        'image': {
                            'url': asset_info['asset_image']
                        },
                        'footer': {
                            'text': f'The Great Ape Society Sales Bot\nPrices from CoinGecko',
                        }
                    }
                ]
            }
        )
        requests.post(self.discord_webhook, data=json_info, headers={"Content-Type": "application/json"})
        logger.info(f"Posted successfully to Discord Webhook, ID={sale_data['sale_id']}, {asset_info['asset_name']}")


if __name__ == "__main__":
    discord_api = DiscordWebhookAPI(group=True)
    discord_api.test_webhook("Test Message")
