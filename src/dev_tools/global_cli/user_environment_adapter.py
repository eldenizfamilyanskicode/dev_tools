from __future__ import annotations

import os
from typing import Protocol

from dev_tools.global_cli.exceptions import GlobalCliSetupError


class UserEnvironmentAdapter(Protocol):
    def get_user_environment_variable(
        self,
        variable_name: str,
    ) -> str | None:
        raise NotImplementedError

    def set_user_environment_variable(
        self,
        variable_name: str,
        variable_value: str,
    ) -> None:
        raise NotImplementedError

    def notify_environment_changed(self) -> None:
        raise NotImplementedError


class WindowsUserEnvironmentAdapter:
    def get_user_environment_variable(
        self,
        variable_name: str,
    ) -> str | None:
        self.ensure_windows()

        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                variable_value: object
                variable_value, _ = winreg.QueryValueEx(key, variable_name)
        except FileNotFoundError:
            return None

        if isinstance(variable_value, str):
            return variable_value

        return str(variable_value)

    def set_user_environment_variable(
        self,
        variable_name: str,
        variable_value: str,
    ) -> None:
        self.ensure_windows()

        import winreg

        registry_value_type: int = winreg.REG_SZ
        if "%" in variable_value:
            registry_value_type = winreg.REG_EXPAND_SZ

        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            "Environment",
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.SetValueEx(
                key,
                variable_name,
                0,
                registry_value_type,
                variable_value,
            )

        os.environ[variable_name] = variable_value

    def notify_environment_changed(self) -> None:
        self.ensure_windows()

        import ctypes

        hwnd_broadcast: int = 0xFFFF
        wm_setting_change: int = 0x001A
        smto_abort_if_hung: int = 0x0002
        timeout_milliseconds: int = 5000
        result_pointer = ctypes.c_ulong()

        send_result: int = ctypes.windll.user32.SendMessageTimeoutW(
            hwnd_broadcast,
            wm_setting_change,
            0,
            "Environment",
            smto_abort_if_hung,
            timeout_milliseconds,
            ctypes.byref(result_pointer),
        )

        if send_result == 0:
            raise GlobalCliSetupError(
                "User environment was written, but Windows did not accept the "
                "environment change notification."
            )

    def ensure_windows(self) -> None:
        if os.name != "nt":
            raise GlobalCliSetupError(
                "User-level environment setup is currently supported only on Windows."
            )
