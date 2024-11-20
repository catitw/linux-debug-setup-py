from enum import Enum
import json
import os

from scripts.paths import get_state_dir


class State(Enum):
    pass


class KernelState(State):
    DEFAULT_NOT_INIT = "default_not_init"
    SRC_CLONED = "src_cloned"
    SRC_CONFIGURED = "src_configured"
    SRC_BUILT = "src_built"


class KernelMachine:
    _state_file = f"{get_state_dir()}/kernel_state.json"

    @staticmethod
    def get_state():
        """
        Reads the current state from a file and returns
        the corresponding enum value.
        """
        try:
            if not os.path.exists(KernelMachine._state_file):
                return (
                    KernelState.DEFAULT_NOT_INIT
                )  # If the file doesn't exist, return default state

            with open(KernelMachine._state_file, "r") as f:
                data = json.load(f)
                state = KernelState(data["state"])
                return state
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            print(f"Error reading the state: {e}")
            return KernelState.DEFAULT_NOT_INIT  # default state when error

    @staticmethod
    def set_state(state: KernelState):
        """
        Saves the state to a file
        """
        try:
            # Ensure the directory exists
            os.makedirs(get_state_dir(), exist_ok=True)
            with open(KernelMachine._state_file, "w") as f:
                json.dump({"state": state.value}, f)
        except Exception as e:
            print(f"Error saving the state: {e}")

    @staticmethod
    def clear_state():
        os.remove(KernelMachine._state_file)
