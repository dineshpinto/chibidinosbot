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

import locale
import logging
import os
import sys
from typing import Union

import requests
import tweepy

from config import API_KEY, API_KEY_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET

locale.setlocale(locale.LC_ALL, '')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)


class TwitterAPI:
    def __init__(self):
        self.api = self.authenticate()
        self.image_folder = "apes"

    @staticmethod
    def authenticate() -> Union[tweepy.API, bool]:
        auth = tweepy.OAuthHandler(API_KEY, API_KEY_SECRET)
        auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

        api = tweepy.API(auth)
        try:
            api.verify_credentials()
            return api
        except Exception as exc:
            logger.error(f"Exception: {exc}")
            return False

    def download_image(self, sale: dict) -> str:
        asset = sale["asset_info"]

        url = asset["asset_image"]
        name = asset["asset_name"]
        response = requests.get(url)
        image_path = os.path.join(self.image_folder, f"{name}.jpg")

        with open(image_path, "wb") as f:
            f.write(response.content)
        logger.info(f"Downloaded image from {url} and saved to {image_path}")
        return image_path

    @staticmethod
    def format_tweet_text(sale: dict) -> str:
        asset = sale["asset_info"]
        seller = sale["seller_info"]
        buyer = sale["buyer_info"]

        addr_chars = 8
        if seller["seller_username"]:
            seller_name = f"{seller['seller_address'][:addr_chars]} ({seller['seller_username']})"
        else:
            seller_name = seller["seller_address"][:addr_chars]

        if buyer["buyer_username"]:
            buyer_name = f"{buyer['buyer_address'][:addr_chars]} ({buyer['buyer_username']})"
        else:
            buyer_name = buyer["buyer_address"][:addr_chars]

        if sale["sale_price_usd"]:
            sale_price_usd = f" ({locale.currency(sale['sale_price_usd'], grouping=True)}) "
        else:
            sale_price_usd = " "

        text = f"{asset['asset_name']} bought for {sale['sale_price']:.3g} {sale['payment_token']}{sale_price_usd}" \
               f"by {buyer_name} from {seller_name}. {asset['asset_link']} #GreatApeSociety #NFTs #Ethereum"
        logger.info(text)
        return text

    def tweet_with_media(self, sale_data: dict):
        tweet_text = self.format_tweet_text(sale_data)
        image_path = self.download_image(sale_data)

        self.api.update_with_media(filename=image_path, status=tweet_text)
        logger.info(f"Posted successfully to Twitter, ID={sale_data['sale_id']}")


if __name__ == "__main__":
    twitter_api = TwitterAPI()
    twitter_api.api.update_status(status="This is a test tweet")
