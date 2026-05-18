from __future__ import annotations

from dev_tools.cli.contracts import CliContribution
from dev_tools.cli.models import CliMenuContext, CliMenuItem


class InteractiveMenuRunner:
    def __init__(self, cli_contributions: list[CliContribution]) -> None:
        self.cli_contributions: tuple[CliContribution, ...] = tuple(cli_contributions)

    def run_menu(self, menu_context: CliMenuContext) -> int:
        while True:
            menu_items: tuple[CliMenuItem, ...] = self.collect_menu_items()
            self.print_menu(menu_items)
            selected_menu_item: str = input("Select action: ").strip()

            if selected_menu_item == "0":
                return 0

            selected_item: CliMenuItem | None = self.find_selected_item(
                menu_items=menu_items,
                selected_menu_item=selected_menu_item,
            )

            if selected_item is None:
                print("Unknown menu item.")
                continue

            selected_item.handler(menu_context)

    def collect_menu_items(self) -> tuple[CliMenuItem, ...]:
        menu_items: list[CliMenuItem] = []

        for cli_contribution in self.cli_contributions:
            contribution_menu_items: tuple[CliMenuItem, ...]
            contribution_menu_items = cli_contribution.get_menu_items()

            for contribution_menu_item in contribution_menu_items:
                menu_items.append(contribution_menu_item)

        menu_items.sort(key=self.get_menu_item_sort_key)
        return tuple(menu_items)

    def get_menu_item_sort_key(self, menu_item: CliMenuItem) -> tuple[int, str]:
        return menu_item.order, menu_item.title.lower()

    def find_selected_item(
        self,
        menu_items: tuple[CliMenuItem, ...],
        selected_menu_item: str,
    ) -> CliMenuItem | None:
        if not selected_menu_item.isdecimal():
            return None

        selected_index: int = int(selected_menu_item) - 1

        if selected_index < 0:
            return None

        if selected_index >= len(menu_items):
            return None

        return menu_items[selected_index]

    def print_menu(self, menu_items: tuple[CliMenuItem, ...]) -> None:
        print("")
        print("--- dev-tools menu ---")

        menu_item_count: int = len(menu_items)
        for menu_item_index in range(menu_item_count):
            menu_item_number: int = menu_item_index + 1
            menu_item: CliMenuItem = menu_items[menu_item_index]
            print(f"{menu_item_number}. {menu_item.title}")

        print("0. Exit")
        print("")
