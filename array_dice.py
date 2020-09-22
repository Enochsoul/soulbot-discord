"""Module for random dice rolling via random number arrays."""
import random

rand_arrays = {
    'd20': [random.randint(1, 20) for _ in range(1000)],
    'd12': [random.randint(1, 12) for _ in range(1000)],
    'd10': [random.randint(1, 10) for _ in range(1000)],
    'd8': [random.randint(1, 8) for _ in range(1000)],
    'd6': [random.randint(1, 6) for _ in range(1000)]}


def die_roll(die_count, die_size):
    """Used for generating random numbers for dice rolling.

    :param die_count: Number of random integers to generate.
    :type die_count: int
    :param die_size: Max value of random number generated.
    :type die_size: int
    :return: List of individual results and sum of results.
    :rtype: (list, int)
    """
    global rand_arrays
    result = []
    if die_size == 20:
        result = random.sample(rand_arrays['d20'], die_count)
    elif die_size == 12:
        result = random.sample(rand_arrays['d12'], die_count)
    elif die_size == 10:
        result = random.sample(rand_arrays['d10'], die_count)
    elif die_size == 8:
        result = random.sample(rand_arrays['d8'], die_count)
    elif die_size == 6:
        result = random.sample(rand_arrays['d6'], die_count)
    else:
        for i in range(0, die_count):
            result.append(random.randint(1, die_size))
    total = sum(result)
    bold_item = [f"**{item}**" if item == die_size else str(item) for item in result]
    result_list = "+".join(bold_item)
    return result_list, total
