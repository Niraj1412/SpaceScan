from __future__ import annotations


def validate_result(data: dict) -> list[str]:
    errors: list[str] = []
    for key in ("schema_version", "capture", "property", "concealed_damage_flags", "scope_line_items", "diagnostics"):
        if key not in data:
            errors.append(f"missing top-level key: {key}")
    rooms = data.get("property", {}).get("rooms", [])
    if not rooms:
        errors.append("property.rooms must contain at least one room")
    room_ids = {room.get("id") for room in rooms}
    surface_ids: set[str] = set()

    def check_interval(measurement: dict, path: str) -> None:
        if not all(k in measurement for k in ("value", "low", "high", "unit", "confidence", "method")):
            errors.append(f"{path} is not a complete interval")
        elif not measurement["low"] <= measurement["value"] <= measurement["high"]:
            errors.append(f"{path} interval does not contain value")
        elif not 0 <= measurement["confidence"] <= 1:
            errors.append(f"{path} confidence is outside [0,1]")

    for room_index, room in enumerate(rooms):
        local_surface_ids: set[str] = set()
        for key in ("id", "polygon", "walls", "floor_area", "ceiling_height", "openings", "damages"):
            if key not in room:
                errors.append(f"room[{room_index}] missing {key}")
        for field in ("floor_area", "ceiling_height"):
            check_interval(room.get(field, {}), f"room[{room_index}].{field}")
        for wall_index, wall in enumerate(room.get("walls", [])):
            local_surface_ids.add(wall.get("id"))
            check_interval(wall.get("length", {}), f"room[{room_index}].walls[{wall_index}].length")
            check_interval(wall.get("surface_area", {}), f"room[{room_index}].walls[{wall_index}].surface_area")
        for opening_index, opening in enumerate(room.get("openings", [])):
            if opening.get("wall_id") not in local_surface_ids:
                errors.append(f"room[{room_index}].openings[{opening_index}] references an unknown wall")
            for field in ("offset", "width", "height"):
                check_interval(opening.get(field, {}), f"room[{room_index}].openings[{opening_index}].{field}")
        for damage_index, damage in enumerate(room.get("damages", [])):
            if damage.get("surface_id") not in local_surface_ids:
                errors.append(f"room[{room_index}].damages[{damage_index}] references an unknown surface")
            check_interval(damage.get("area", {}), f"room[{room_index}].damages[{damage_index}].area")
        surface_ids.update(local_surface_ids)
    for index, adjacency in enumerate(data.get("property", {}).get("adjacencies", [])):
        if adjacency.get("room_a") not in room_ids or adjacency.get("room_b") not in room_ids:
            errors.append(f"adjacency[{index}] references an unknown room")
        if adjacency.get("room_a") == adjacency.get("room_b"):
            errors.append(f"adjacency[{index}] is a self-loop")
    if "footprint_area" in data.get("property", {}):
        check_interval(data["property"]["footprint_area"], "property.footprint_area")
    for index, item in enumerate(data.get("scope_line_items", [])):
        if item.get("surface_id") not in surface_ids:
            errors.append(f"scope_line_items[{index}] references an unknown surface")
    return errors
