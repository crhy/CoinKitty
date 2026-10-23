"""Shared layout-test helpers: bounded widget-tree walks."""

from __future__ import annotations


def is_inside(widget, ancestor) -> bool:
    """True if ``widget`` is a descendant of ``ancestor`` (bounded parent walk)."""
    steps = 0
    current = widget.get_parent()
    while current is not None and steps < 100:
        if current is ancestor:
            return True
        current = current.get_parent()
        steps += 1
    return False


def find_all(root, type_) -> list:
    """Every widget of ``type_`` at or below ``root`` (bounded tree walk)."""
    found = []
    budget = 5000
    stack = [root]
    while stack and budget > 0:
        widget = stack.pop()
        budget -= 1
        if isinstance(widget, type_):
            found.append(widget)
        child = widget.get_first_child()
        while child is not None and budget > 0:
            budget -= 1
            stack.append(child)
            nxt = child.get_next_sibling()
            if nxt is None or nxt is child:
                break
            child = nxt
    return found
