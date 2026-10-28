"""Public failures are deliberate and contain no event content."""


class CalendarReconcileError(ValueError):
    """Base validation error for this package."""


class BoundsError(CalendarReconcileError):
    """A caller exceeded a configured resource bound."""


class IdentityError(CalendarReconcileError):
    """An opaque identity or correction identity is unsafe."""
