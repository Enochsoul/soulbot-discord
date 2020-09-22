"""Module for using randint to generate die rolls."""
import random


def die_roll(die_count, die_size):
    """Used for generating random numbers for dice rolling.

    :param die_count: Number of random integers to generate.
    :type die_count: int
    :param die_size: Max value of random number generated.
    :type die_size: int
    :return: List of individual results and sum of results.
    :rtype: (list, int)
    """
    count = die_count
    result = []
    while count > 0:
        result.append(random.randint(1, die_size))
        count -= 1
    total = sum(result)
    bold_item = [f"**{item}**" if item == die_size else str(item) for item in result]
    result_list = "+".join(bold_item)
    return result_list, total
