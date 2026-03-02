from api.models.events.event import Event


def can_delete_event(event: Event) -> str | None:
    count = event.reservations.count()
    if count > 0:
        return (
            f"Cannot delete '{event.name}': it has {count} reservation(s) associated."
        )
    return None
