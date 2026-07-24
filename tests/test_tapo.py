"""Unit tests for Tapo P110 integration."""

import pytest
from ameva_wol.tapo_plug import TapoManager

def test_tapo_manager_not_configured():
    manager = TapoManager(email=None, password=None, devices={})
    assert not manager.is_configured()

def test_tapo_manager_get_ip_single():
    manager = TapoManager(email="test@test.com", password="pass", devices={"p110": "192.168.0.5"})
    assert manager.is_configured()
    assert manager._get_ip_for_alias(None) == "192.168.0.5"
    assert manager._get_ip_for_alias("p110") == "192.168.0.5"

def test_tapo_manager_get_ip_multiple():
    devices = {"p110_1": "192.168.0.5", "p110_2": "192.168.0.6"}
    manager = TapoManager(email="test@test.com", password="pass", devices=devices)
    
    # Must specify alias when multiple devices exist
    with pytest.raises(ValueError, match="Multiple devices configured"):
        manager._get_ip_for_alias(None)
        
    assert manager._get_ip_for_alias("p110_1") == "192.168.0.5"
    assert manager._get_ip_for_alias("p110_2") == "192.168.0.6"

def test_tapo_manager_invalid_alias():
    manager = TapoManager(email="test@test.com", password="pass", devices={"p110": "192.168.0.5"})
    with pytest.raises(ValueError, match="Device alias 'unknown' not found"):
        manager._get_ip_for_alias("unknown")
