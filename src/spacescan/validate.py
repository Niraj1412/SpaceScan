from __future__ import annotations


def validate_result(data: dict) -> list[str]:
    errors: list[str] = []
    for key in ("schema_version", "capture", "property", "concealed_damage_flags", "scope_line_items", "diagnostics"):
        if key not in data:
            errors.append(f"missing top-level key: {key}")
    rooms = data.get("property", {}).get("rooms", [])
    if not rooms:
        errors.append("property.rooms must contain at least one room")
    for room_index, room in enumerate(rooms):
        for key in ("id", "polygon", "walls", "floor_area", "ceiling_height", "openings", "damages"):
            if key not in room:
                errors.append(f"room[{room_index}] missing {key}")
        for field in ("floor_area", "ceiling_height"):
            measurement = room.get(field, {})
            if not all(k in measurement for k in ("value", "low", "high", "unit", "confidence", "method")):
                errors.append(f"room[{room_index}].{field} is not a complete interval")
            elif not measurement["low"] <= measurement["value"] <= measurement["high"]:
                errors.append(f"room[{room_index}].{field} interval does not contain value")
    return errors

