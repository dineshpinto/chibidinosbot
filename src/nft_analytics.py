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
from json import JSONDecodeError
from typing import Tuple
import numpy as np
from tqdm import tqdm

from .opensea_api import OpenSeaAPI

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("logfile.log", mode="a"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class NFTAnalytics(OpenSeaAPI):
    def __init__(self, asset_contract_address: str):
        super().__init__(asset_contract_address)

    def fetch_data(self, max_offset: int = 10000) -> list:
        local_assets = []

        pbar = tqdm(range(0, max_offset + 1, 50))
        for offset in pbar:
            pbar.set_description(f"{offset}")
            try:
                asset_data = self.get_asset_data(offset=offset, limit=50)
            except JSONDecodeError:
                logger.error(f"Only fetched data till offset={offset - 1}. "
                             f"Warning={self.get_asset_data(offset=offset, limit=50)}")
                return local_assets

            if "assets" not in asset_data:
                logger.error(f"Only fetched data till offset={offset - 1}. Warning={asset_data}")
                return local_assets

            for asset in asset_data["assets"]:
                local_assets.append(asset)

        return local_assets

    def fetch_events(self, max_offset: int = 10000) -> list:
        local_events = []

        pbar = tqdm(range(0, max_offset + 1, 300))
        for offset in pbar:
            pbar.set_description(f"{offset}")
            try:
                event_data = self.get_event_data(offset=offset, limit=300)
            except JSONDecodeError:
                logger.error(f"Only fetched data till offset={offset - 1}. "
                             f"Warning={self.get_asset_data(offset=offset, limit=50)}")
                return local_events

            if "asset_events" not in event_data:
                logger.error(f"Only fetched data till offset={offset - 1}. Warning={event_data}")
                return local_events

            for event in event_data["asset_events"]:
                local_events.append(event)

        return local_events

    @staticmethod
    def save_json(asset_data: list, filename: str = "data.json"):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(asset_data, f, ensure_ascii=False, indent=4)

    @staticmethod
    def load_json(filename: str = "data.json") -> list:
        with open(filename) as f:
            asset_data = json.load(f)

        return asset_data

    @staticmethod
    def remove_asset_type_from_traits(asset_data: list, trait_type_to_remove: str):
        for asset in asset_data:
            if asset["traits"]:
                for traits in asset["traits"]:
                    if traits["trait_type"] == trait_type_to_remove:
                        asset["traits"].remove(traits)

        return asset_data

    @staticmethod
    def get_trait_values_for_type(asset_data: list, trait_type: str) -> list:
        trait_values = []
        for asset in asset_data:
            for traits in asset["traits"]:
                if traits["trait_type"] == trait_type and str(traits["value"]) not in trait_values:
                    trait_values.append(str(traits["value"]))

        return trait_values

    def get_trait_type_median_price(self, asset_data: list, trait_type: str) -> dict:
        trait_value_prices = {}
        for value in self.get_trait_values_for_type(asset_data, trait_type):
            listing_prices_trait = []

            for asset in asset_data:
                if asset["sell_orders"]:
                    for traits in asset["traits"]:
                        if traits["trait_type"] == trait_type and traits["value"] == value:
                            listing_prices_trait.append(float(asset["sell_orders"][0]["base_price"]) / 1e18)

            trait_value_prices[value] = np.nanmedian(np.array(listing_prices_trait))
        return dict(sorted(trait_value_prices.items(), key=lambda item: item[1], reverse=True))

    def get_median_prices(self, asset_data: list, traits_dict: dict) -> np.ndarray:
        median_prices = []
        for trait_type, trait_value in traits_dict.items():
            median_prices.append(self.get_trait_type_median_price(asset_data, trait_type)[trait_value])

        return np.array(median_prices)

    def get_traits_with_median_prices(self, asset_data: list, asset: dict) -> dict:
        traits = {}
        for trait in asset["traits"]:
            traits[trait["trait_type"]] = str(trait["value"])

        trait_prices = {}

        for trait_type, trait_value in traits.items():
            price = self.get_trait_type_median_price(asset_data, trait_type)[trait_value]
            trait_prices[trait_value + " " + trait_type] = price

        return trait_prices

    @staticmethod
    def get_total_unique_trait_count_and_rarities(asset_data: list) -> Tuple[int, np.ndarray]:
        total_traits_count = 0
        traits_counted = []

        for asset in asset_data:
            if asset["traits"]:
                for traits in asset["traits"]:
                    if traits["value"] not in traits_counted:
                        traits_counted.append(traits["value"])
                        total_traits_count += traits["trait_count"]

        rarities = []
        for asset in asset_data:
            if asset["traits"]:
                trait_count = 0
                for traits in asset["traits"]:
                    trait_count += traits["trait_count"]
                rarities.append(total_traits_count / trait_count)

        return int(total_traits_count), np.array(rarities)

    @staticmethod
    def rescale_value(value: float, array: np.ndarray, min_val: int = 0, max_val: int = 100):
        return (max_val - min_val) / (np.max(array) - np.min(array)) * (value - np.max(array)) + max_val

    def get_rarity_score(self, asset: dict, rarity: np.ndarray, total_traits_count: int) -> int:
        if asset["traits"]:
            trait_count = 0
            for traits in asset["traits"]:
                trait_count += traits["trait_count"]
            return round(self.rescale_value(total_traits_count / trait_count, rarity))
        else:
            return -1
