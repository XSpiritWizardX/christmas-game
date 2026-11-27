"""Between-round ballots. The original schedule wins ties and empty votes."""


def options(room):
    if (room.selected_mode != "random" or room.status != "between_rounds"
            or room.task_running or not 0 < room.current_round < len(room.round_order)):
        return []
    scheduled = room.round_order[room.current_round]
    choices = list(dict.fromkeys(room.round_order[room.current_round:]))
    choices = [mode for mode in choices if mode != room.round_type][:2]
    if len(choices) < 2:
        for mode in reversed(room.round_order[:room.current_round]):
            if mode != room.round_type and mode not in choices:
                choices.append(mode)
                if len(choices) == 2:
                    break
    if scheduled not in choices:
        choices.insert(0, scheduled)
    if room.round_type not in choices:
        choices.append(room.round_type)
    return choices


def ballot(room):
    votes = [mode for sid, mode in room.round_votes.items() if sid in room.players]
    return [{"mode": mode, "votes": votes.count(mode)} for mode in options(room)]


def winner(room):
    choices = ballot(room)
    return max(choices, key=lambda choice: choice["votes"])["mode"] if choices else None


def apply(room):
    mode = winner(room)
    if mode:
        index = room.current_round
        if mode in room.round_order[index:]:
            other = room.round_order.index(mode, index)
            room.round_order[index], room.round_order[other] = mode, room.round_order[index]
        else:
            room.round_order[index] = mode
    room.round_votes.clear()
