import random
import re
from dataclasses import dataclass
from itertools import chain
from typing import List

import numpy as np
from scipy.stats import truncnorm


class InvalidDiceFormat(Exception):
    pass


class InvalidRollType(Exception):
    pass


@dataclass
class RollResult:
    """Data class to represent dice roll results."""

    rolls: List[str]
    total: int
    roll_type: str
    modifier: int | None
    string: str = ""


class Dice:
    """A comprehensive dice rolling system with support for various roll types."""

    def __init__(self) -> None:
        # Regex patterns for different roll formats
        self.normal_pattern = re.compile(
            r"^(?P<dice_count>[0-9]+)(?P<roll_type>\D{1,2})(?P<dice_size>[0-9]+)(?P<modifier>[+-][0-9]+)*$"
        )
        self.multi_dice_pattern = re.compile(r"^(?:\d+\D+\d+[-+]?\d*/?)+$")

    def roll(self, roll_string: str) -> RollResult:
        """
        Main entry point for rolling dice.

        Args:
            roll_string: A string representing the dice roll (e.g., '3d6', '1ad20+5', '2d4/1d8')

        Returns:
            RollResult: A formatted result containing roll details and total

        Raises:
            InvalidDiceFormat: If the roll string format is invalid
            InvalidRollType: If an unsupported roll type is specified
        """
        if not roll_string or not isinstance(roll_string, str):
            raise InvalidDiceFormat("Roll string must be a non-empty string")

        # Clean up the input string
        roll_string = roll_string.strip().lower()

        try:
            result = self._parse_and_roll(roll_string)
            return self._output_formatter(result)
        except (InvalidDiceFormat, InvalidRollType):
            raise
        except Exception as e:
            raise InvalidDiceFormat(
                f"Error processing roll string '{roll_string}': {str(e)}"
            )

    def _parse_and_roll(self, roll_string: str) -> RollResult:
        """Parse the roll string and execute the appropriate roll."""
        # Try to match different patterns
        normal_match = self.normal_pattern.match(roll_string)
        multi_match = self.multi_dice_pattern.match(roll_string)

        if normal_match:
            return self._handle_normal_roll(normal_match)
        elif multi_match:
            return self._handle_multi_roll(multi_match)
        else:
            raise InvalidDiceFormat(
                "Error: Dice rolls should be in the format 'XdY' or 'XdY+Z' or 'XdY-Z'"
            )

    def _handle_normal_roll(self, match) -> RollResult:
        """Handle a normal dice roll (e.g., 3d6, 1ad20)."""
        count, roll_type, size, modifier = match.groups()
        modifier = int(modifier) if modifier else 0
        dice_rolls = self._generate_dice_rolls(int(count), int(size))
        return self._apply_roll_type(int(size), dice_rolls, roll_type, modifier)

    def _handle_multi_roll(self, match) -> RollResult:
        """Handle multiple dice rolls separated by '/' (e.g., 1d6/1d8/2d4)."""
        rolls = match.string.split("/")
        roll_results = []

        for roll in rolls:
            if not self.normal_pattern.match(roll):
                raise InvalidDiceFormat("Error: Unrecognized dice format.")
            roll_results.append(self._parse_and_roll(roll))

        # Combine results
        combined_rolls = list(
            chain.from_iterable(result.rolls for result in roll_results)
        )
        combined_totals = sum(result.total for result in roll_results)
        combined_types = "/".join(result.roll_type for result in roll_results)
        combined_modifiers = sum(result.modifier for result in roll_results)

        return RollResult(
            combined_rolls, combined_totals, combined_types, combined_modifiers
        )

    def _generate_dice_rolls(self, count: int, size: int) -> List[int]:
        """Generate dice rolls using numpy/scipy for multi-die or random for single die."""
        if count == 1:
            return self._roll_single_die(size)
        else:
            return self._roll_multiple_dice(count, size)

    @staticmethod
    def _roll_single_die(die_size: int) -> List[int]:
        """Roll a single die using standard random."""
        return [random.randint(1, die_size)]

    @staticmethod
    def _roll_multiple_dice(die_count: int, die_size: int) -> List[int]:
        """Roll multiple dice using numpy and scipy for better distribution."""
        mean = np.mean(range(1, die_size + 1))
        std = np.std(range(1, die_size + 1))
        a, b = (1 - mean) / std, ((die_size + 1) - mean) / std

        return (
            truncnorm.rvs(a, b, loc=mean, scale=std, size=die_count)
            .astype(int)
            .tolist()
        )

    def _apply_roll_type(
        self,
        die_size: int,
        roll_result: List[int],
        roll_type: str,
        modifier: int | None,
    ) -> RollResult:
        """Apply special roll type effects (advantage, disadvantage, exploding, etc.)."""
        match roll_type:
            case "d":  # Normal roll
                bold_result = [
                    f"**{roll}**" if roll == die_size else str(roll)
                    for roll in roll_result
                ]
                return RollResult(bold_result, sum(roll_result), "Default", modifier)

            case "dd":  # Disadvantage roll
                if len(roll_result) != 1:
                    raise InvalidDiceFormat(
                        "Error: Disadvantage roll must only be a single die."
                    )
                roll_result.extend(self._roll_single_die(die_size))
                bold_result = [
                    f"**{roll}**" if roll == die_size else str(roll)
                    for roll in roll_result
                ]
                return RollResult(
                    bold_result, min(roll_result), "Disadvantage", modifier
                )

            case "ad":  # Advantage roll
                if len(roll_result) != 1:
                    raise InvalidDiceFormat(
                        "Error: Advantage roll must only be a single die."
                    )
                roll_result.extend(self._roll_single_die(die_size))
                bold_result = [
                    f"**{roll}**" if roll == die_size else str(roll)
                    for roll in roll_result
                ]
                return RollResult(bold_result, max(roll_result), "Advantage", modifier)

            case "ed":  # Exploding roll
                explode_count = roll_result.count(die_size)
                while explode_count > 0:
                    explode_count -= 1
                    exploded = self._roll_single_die(die_size)
                    roll_result.extend(exploded)
                    explode_count += exploded.count(die_size)

                bold_result = [
                    f"**{roll}**" if roll == die_size else str(roll)
                    for roll in roll_result
                ]
                return RollResult(bold_result, sum(roll_result), "Exploding", modifier)

            case "ex":  # 10X System (placeholder for future implementation)
                bold_result = [
                    f"**{roll}**" if roll == die_size else str(roll)
                    for roll in roll_result
                ]
                return RollResult(bold_result, sum(roll_result), "10x System", modifier)

            case "dl":  # Drop lowest roll.
                lowest = min(roll_result)
                roll_result.remove(lowest)
                bold_result = [
                    f"**{roll}**" if roll == die_size else str(roll)
                    for roll in roll_result
                ]
                return RollResult(
                    bold_result, sum(roll_result), "Drop Lowest", modifier
                )

            case "dh":  # Drop highest roll.
                lowest = max(roll_result)
                roll_result.remove(lowest)
                bold_result = [
                    f"**{roll}**" if roll == die_size else str(roll)
                    for roll in roll_result
                ]
                return RollResult(
                    bold_result, sum(roll_result), "Drop Highest", modifier
                )

            case _:  # Invalid type
                raise InvalidRollType(f"Error: Invalid roll type: {roll_type}")

    @staticmethod
    def _output_formatter(roll_result: RollResult) -> RollResult:
        if roll_result.modifier:
            string_modifier = (
                f"+{roll_result.modifier}"
                if roll_result.modifier > 0
                else f"{roll_result.modifier}"
            )
            if len(roll_result.rolls) == 1:
                roll_result.string = f"rolled w/ {roll_result.roll_type}: **{roll_result.total + roll_result.modifier}**. ({roll_result.total}{string_modifier})"
                return roll_result
            elif len(roll_result.rolls) > 1:
                string_out = "+".join(roll_result.rolls) + string_modifier
                roll_result.string = f"rolled w/ {roll_result.roll_type}: **{roll_result.total + roll_result.modifier}**. ({string_out})"
                return roll_result
            else:
                roll_result.string = "rolled the impossible, please try again."
                return roll_result
        else:
            string_out = "+".join(roll_result.rolls)
            roll_result.string = f"rolled w/ {roll_result.roll_type}: **{roll_result.total}**. ({string_out})"
            return roll_result
