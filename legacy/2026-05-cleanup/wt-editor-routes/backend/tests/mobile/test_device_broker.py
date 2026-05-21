"""DeviceBroker birim testleri."""
from __future__ import annotations

import pytest

from app.domains.mobile.device_broker import get_broker
from app.domains.mobile.schemas import PhysicalEnrollRequest


pytestmark = pytest.mark.P1


def test_seed_has_ten_devices():
    devices = get_broker().list()
    assert len(devices) == 10


def test_seed_platform_distribution():
    devices = get_broker().list()
    android = [d for d in devices if d.platform == "android"]
    ios = [d for d in devices if d.platform == "ios"]
    assert len(android) == 6
    assert len(ios) == 4


def test_legacy_nexus_is_offline_by_default():
    broker = get_broker()
    nexus = broker.get("and-nexus_5x")
    assert nexus is not None
    assert nexus.status == "offline"


def test_get_nonexistent_returns_none():
    assert get_broker().get("nope") is None


def test_pick_available_respects_platform_filter():
    broker = get_broker()
    android_pick = broker.pick_available(platform="android", count=10)
    ios_pick = broker.pick_available(platform="ios", count=10)
    both = broker.pick_available(platform="both", count=10)

    assert all(d.platform == "android" for d in android_pick)
    assert all(d.platform == "ios" for d in ios_pick)
    # 6 android - 1 offline nexus = 5 idle; 4 ios all idle
    assert len(android_pick) == 5
    assert len(ios_pick) == 4
    assert len(both) == 9


def test_pick_available_respects_count_limit():
    picks = get_broker().pick_available(count=3)
    assert len(picks) == 3


def test_enroll_physical_creates_device():
    broker = get_broker()
    pre_count = len(broker.list())
    req = PhysicalEnrollRequest(
        name="Lab-01 Samsung S24",
        platform="android",
        os_version="14",
        udid="R58M3ABC123",
        appium_url="http://lab-1:4750",
    )
    device = broker.enroll_physical(req)

    assert device.id.startswith("phy-")
    assert device.kind == "physical"
    assert device.platform == "android"
    assert device.name == "Lab-01 Samsung S24"
    assert device.status == "idle"
    assert len(broker.list()) == pre_count + 1


def test_enroll_physical_defaults_profile_from_name():
    broker = get_broker()
    req = PhysicalEnrollRequest(
        name="iPhone 15 Max",
        platform="ios",
        os_version="17",
        udid="UDID-1",
        appium_url="http://lab:4723",
    )
    device = broker.enroll_physical(req)
    assert device.profile == "iphone_15_max"


def test_update_status_transitions():
    broker = get_broker()
    updated = broker.update_status("and-pixel_8", "running", steps_done=5, steps_total=10)
    assert updated is not None
    assert updated.status == "running"
    assert updated.steps_done == 5
    assert updated.steps_total == 10


def test_update_status_unknown_device_returns_none():
    assert get_broker().update_status("ghost", "idle") is None


def test_stats_shape():
    stats = get_broker().stats()
    assert stats["total"] == 10
    assert stats["online"] == 9
    assert stats["offline"] == 1
    assert stats["by_platform"]["android"] == 6
    assert stats["by_platform"]["ios"] == 4


def test_reboot_transitions_through_booting():
    broker = get_broker()
    broker.reboot("and-pixel_8")
    dev = broker.get("and-pixel_8")
    assert dev is not None
    # reboot sonrasında hemen booting — eventually idle olur (background thread)
    assert dev.status == "booting"


def test_broker_is_singleton():
    b1 = get_broker()
    b2 = get_broker()
    assert b1 is b2
