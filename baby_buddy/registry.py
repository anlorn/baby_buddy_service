"""Command registry mapping command name strings to handler callables."""

from typing import Callable

from .changes import diaper_change_solid, diaper_change_wet_solid
from .feedings import (
    feeding_bottle_breast_milk,
    feeding_bottle_formula,
    feeding_finish_last,
    feeding_left_breast,
    feeding_right_breast,
)
from .sleep import sleep_finish, sleep_start

COMMANDS: dict[str, Callable] = {
    "feeding_left_breast": feeding_left_breast,
    "feeding_right_breast": feeding_right_breast,
    "feeding_bottle_breast_milk": feeding_bottle_breast_milk,
    "feeding_bottle_formula": feeding_bottle_formula,
    "feeding_finish_last": feeding_finish_last,
    "diaper_change_wet_solid": diaper_change_wet_solid,
    "diaper_change_solid": diaper_change_solid,
    "sleep_start": sleep_start,
    "sleep_finish": sleep_finish,
}
