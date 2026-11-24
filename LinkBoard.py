#Link Board state for the map tab grid; free of kivy so it also runs headless
from ast import literal_eval
from typing import Any, Iterable, List, NamedTuple, Optional, Set

from .Items import SPIRITLIST, get_spirit_by_id, item_table
from .Locations import RIKU_COMPLETION_LOCS, SORA_COMPLETION_LOCS, location_data_table
from .Rules import gated_nodes

NODES_PER_BOARD = 16
PROGRESSION_FLAG = 1

CHARACTER_NAMES = {1: "Sora", 2: "Riku"}
COMPLETION_IDS = {
    1: [location_data_table[name].code for name in SORA_COMPLETION_LOCS],
    2: [location_data_table[name].code for name in RIKU_COMPLETION_LOCS],
}
RECIPE_SPIRITS = {item_table[f"{name} Recipe"]: spirit_id for name, spirit_id in SPIRITLIST.items()}


class Gate(NamedTuple):
    character: int
    worlds: int
    beaten: int
    nodes: range

    @property
    def is_open(self) -> bool:
        return self.beaten >= self.worlds

    @property
    def description(self) -> str:
        who = CHARACTER_NAMES[self.character]
        if self.is_open:
            return f"{who} can open this gate ({self.beaten}/{self.worlds} worlds)"
        remaining = self.worlds - self.beaten
        return f"{who} must beat {remaining} more world{'s' if remaining > 1 else ''} ({self.beaten}/{self.worlds})"


class Node(NamedTuple):
    number: int
    item: Optional[str]
    owner: Optional[str]
    progression: bool
    checked: bool
    gated: bool


class Spirit(NamedTuple):
    id: int
    name: str
    gates: List[Gate]
    nodes: List[Node]

    def matches(self, query: str, progression_only: bool) -> bool:
        if progression_only and not any(node.progression and not node.checked for node in self.nodes):
            return False
        query = query.casefold()
        return query in self.name.casefold() or any(query in node.item.casefold() for node in self.nodes if node.item)


def gate_requirements(slot_data: dict) -> List[List[int]]:
    try:
        return literal_eval(slot_data["gate_reqs"])
    except KeyError: #Seeds that predate gate_reqs
        return []


def obtained_spirits(items_received: Iterable[Any]) -> Set[int]:
    return {RECIPE_SPIRITS[item.item] for item in items_received if item.item in RECIPE_SPIRITS}


def board_location_ids(spirit_name: str) -> List[int]:
    return [location_data_table[f"{spirit_name} Node {node:02d}"].code for node in range(1, NODES_PER_BOARD + 1)]


def worlds_beaten(locations_checked: Set[int], character: int) -> int:
    return sum(location in locations_checked for location in COMPLETION_IDS[character])


def load_spirits(ctx: Any) -> List[Spirit]:
    """Boards of the spirits obtained so far, in spirit order."""
    gate_reqs = {req[0]: req[1:] for req in gate_requirements(ctx.slot_data_info)}
    spirits = []
    for spirit_id in sorted(obtained_spirits(ctx.items_received)):
        name = get_spirit_by_id(spirit_id)
        gates = []
        if spirit_id in gate_reqs:
            character, *world_reqs = gate_reqs[spirit_id]
            beaten = worlds_beaten(ctx.locations_checked, character)
            gates = [Gate(character, worlds, beaten, gated_nodes(name, num)) for num, worlds in enumerate(world_reqs)]
        closed_nodes = {index for gate in gates if not gate.is_open for index in gate.nodes}

        nodes = []
        for index, location in enumerate(board_location_ids(name)):
            scouted = ctx.locations_info.get(location)
            nodes.append(Node(
                number=index + 1,
                item=ctx.item_names.lookup_in_slot(scouted.item, scouted.player) if scouted else None,
                owner=ctx.player_names[scouted.player] if scouted and scouted.player != ctx.slot else None,
                progression=bool(scouted and scouted.flags & PROGRESSION_FLAG),
                checked=location in ctx.locations_checked,
                gated=index in closed_nodes,
            ))
        spirits.append(Spirit(spirit_id, name, gates, nodes))
    return spirits
