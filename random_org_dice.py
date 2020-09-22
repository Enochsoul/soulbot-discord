"""Module for using the Random.org API to generate random numbers."""

import requests
from soulbot import bot_config


def die_roll(die_count, die_size):
    """Used for generating random numbers from random.org's APi for dice rolling.

    :param die_count: Number of random integers to generate.
    :type die_count: int
    :param die_size: Max value of random number generated.
    :type die_size: int
    :return: List of individual results and sum of results.
    :rtype: (list, int)
    """
    json_body = {
        "jsonrpc": "2.0",
        "method": "generateIntegers",
        "params": {
            "apiKey": bot_config['random_org_key'],
            "n": die_count,
            "min": 1,
            "max": die_size,
            "replacement": True
        },
        "id": 1337
    }
    response = requests.post('https://api.random.org/json-rpc/2/invoke', json=json_body)
    result = response.json()['result']['random']['data']
    total = sum(result)
    bold_item = [f"**{item}**" if item == die_size else str(item) for item in result]
    result_list = "+".join(bold_item)
    return result_list, total
