"""Permission-confirmation UX. v1 is keyboard-only — same y/N prompt as
ws_client.py — while everything else is voice. A future voice_confirm(text)
-> bool (speak the request, listen, transcribe yes/no) is a drop-in
replacement for this same signature; no other code needs to change."""

from __future__ import annotations


def keyboard_confirm(description: str) -> bool:
    print(f"\n⚠ Permission required\n{description}")
    answer = input("Allow? [y/N] ").strip().lower()
    return answer in ("y", "yes")
