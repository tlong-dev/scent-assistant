"""Verify the AL_SUB_ALL_WORK_INFO (`52 0A` / `53 0A`) power-byte parsing.

Captured live 2026-08-28 against a real AromaDD diffuser advertising
"Smart.A5.WIFI" (Aroma-Link protocol family): payload byte [11] flipped
01 -> 00 when power was commanded off and back, while the fan/lamp
nibble byte [10] stayed 0x01 throughout. See
custom_components/scent_assistant/protocol_ble.py, AL_SUB_ALL_WORK_INFO
branch of AromaLinkBleProtocol.parse_notification.

Run directly: `python3 tests/test_aroma_link_power_byte.py`
(no pytest dependency required; functions are also pytest-collectible).
"""
from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPONENT_DIR = REPO_ROOT / "custom_components" / "scent_assistant"


def _load_protocol_ble():
    """Import protocol_ble.py without pulling in homeassistant.

    protocol_ble.py itself has no `homeassistant` import, but it does a
    relative `from .const import (...)`, which requires it to live inside
    a real package. The real
    custom_components/scent_assistant/__init__.py imports homeassistant
    and voluptuous, so importing the package normally would drag those
    in (and they may not be installed in a plain test environment).
    Instead, register stub package entries in sys.modules pointing at
    the real directory - Python's import machinery then resolves
    `protocol_ble` and `const` as submodules of that directory without
    ever executing the real __init__.py. const.py is verified
    dependency-free (only stdlib `enum`), so this stays self-contained.
    """
    if "custom_components" not in sys.modules:
        pkg = types.ModuleType("custom_components")
        pkg.__path__ = [str(REPO_ROOT / "custom_components")]
        sys.modules["custom_components"] = pkg

    if "custom_components.scent_assistant" not in sys.modules:
        pkg = types.ModuleType("custom_components.scent_assistant")
        pkg.__path__ = [str(COMPONENT_DIR)]
        sys.modules["custom_components.scent_assistant"] = pkg

    return importlib.import_module("custom_components.scent_assistant.protocol_ble")


_protocol_ble = _load_protocol_ble()
AromaLinkBleProtocol = _protocol_ble.AromaLinkBleProtocol


# Captured live 2026-08-28. Each is a single, complete GATT notification
# (header a5aaac + xor byte, payload, trailer c5ccca) - parse_notification
# strips header/trailer itself via `payload = data[4:-3]`.

# power ON: state was power=true, phase=spraying, work_remaining=8,
# pause_remaining=120, schedule window 07:00-21:00.
FRAME_POWER_ON = bytes.fromhex(
    "a5aaac90520a07ea081c0c2303050101010008007807001500085037cd61972f"
    "00000000010000000000000101000100000000000000c5ccca"
)

# power OFF: state power=false, same schedule window, work_remaining=20.
FRAME_POWER_OFF = bytes.fromhex(
    "a5aaaca8520a07ea081c0c2327050100000014007807001500085037cd61972f"
    "00000000010000000000000101000100000000000000c5ccca"
)


def test_power_on_frame() -> None:
    proto = AromaLinkBleProtocol()
    result = proto.parse_notification(FRAME_POWER_ON)
    assert result["power"] is True, result
    assert result["work_remaining"] == 8, result
    assert result["pause_remaining"] == 120, result
    assert result["start_hour"] == 7, result
    assert result["end_hour"] == 21, result


def test_power_off_frame() -> None:
    proto = AromaLinkBleProtocol()
    result = proto.parse_notification(FRAME_POWER_OFF)
    assert result["power"] is False, result
    assert result["work_remaining"] == 20, result
    assert result["pause_remaining"] == 120, result


if __name__ == "__main__":
    test_power_on_frame()
    test_power_off_frame()
    print("OK: test_power_on_frame, test_power_off_frame")
