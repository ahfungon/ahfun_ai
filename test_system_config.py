#!/usr/bin/env python3
"""
Test script for system configuration management feature.

This script tests:
1. Configuration retrieval (all and by category)
2. Configuration update (single and batch)
3. Configuration reset
4. Configuration validation
5. Frontend page accessibility
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8080"
API_URL = f"{BASE_URL}/api"


def test_get_all_configs():
    """Test retrieving all configurations."""
    print("📋 Testing: Get all configurations...")
    response = requests.get(f"{API_URL}/admin/config/system")
    
    if response.status_code != 200:
        print(f"❌ Failed: HTTP {response.status_code}")
        return False
    
    data = response.json()
    categories = data.get("categories", {})
    
    if not categories:
        print("❌ Failed: No categories returned")
        return False
    
    print(f"✅ Success: Retrieved {len(categories)} categories")
    for category, configs in categories.items():
        print(f"   - {category}: {len(configs)} configs")
    
    return True


def test_get_config_by_category():
    """Test retrieving configurations by category."""
    print("\n📋 Testing: Get configurations by category...")
    response = requests.get(f"{API_URL}/admin/config/system?category=summary")
    
    if response.status_code != 200:
        print(f"❌ Failed: HTTP {response.status_code}")
        return False
    
    data = response.json()
    configs = data.get("configs", [])
    
    if not configs:
        print("❌ Failed: No configs returned")
        return False
    
    print(f"✅ Success: Retrieved {len(configs)} summary configs")
    return True


def test_get_single_config():
    """Test retrieving a single configuration."""
    print("\n📋 Testing: Get single configuration...")
    response = requests.get(f"{API_URL}/admin/config/system/summary_threshold")
    
    if response.status_code != 200:
        print(f"❌ Failed: HTTP {response.status_code}")
        return False
    
    data = response.json()
    
    if data.get("key") != "summary_threshold":
        print("❌ Failed: Wrong config returned")
        return False
    
    print(f"✅ Success: Retrieved config '{data.get('display_name')}'")
    print(f"   Current value: {data.get('value')}")
    return True


def test_update_config():
    """Test updating a configuration."""
    print("\n✏️ Testing: Update configuration...")
    
    # Get current value
    response = requests.get(f"{API_URL}/admin/config/system/summary_threshold")
    original_value = response.json().get("value")
    
    # Update to new value
    new_value = "10000"
    response = requests.put(
        f"{API_URL}/admin/config/system/summary_threshold",
        json={"value": new_value}
    )
    
    if response.status_code != 200:
        print(f"❌ Failed: HTTP {response.status_code}")
        return False
    
    data = response.json()
    
    if not data.get("success"):
        print(f"❌ Failed: {data.get('message')}")
        return False
    
    if data.get("config", {}).get("value") != new_value:
        print("❌ Failed: Value not updated")
        return False
    
    print(f"✅ Success: Updated from {original_value} to {new_value}")
    
    # Restore original value
    requests.put(
        f"{API_URL}/admin/config/system/summary_threshold",
        json={"value": original_value}
    )
    
    return True


def test_batch_update():
    """Test batch updating configurations."""
    print("\n✏️ Testing: Batch update configurations...")
    
    updates = {
        "summary_threshold": "8500",
        "llm_provider_scoring": "deepseek"
    }
    
    response = requests.post(
        f"{API_URL}/admin/config/system/batch",
        json={"configs": updates}
    )
    
    if response.status_code != 200:
        print(f"❌ Failed: HTTP {response.status_code}")
        return False
    
    data = response.json()
    
    if not data.get("success"):
        print(f"❌ Failed: {data.get('message')}")
        return False
    
    updated_count = len(data.get("configs", []))
    if updated_count != len(updates):
        print(f"❌ Failed: Expected {len(updates)} updates, got {updated_count}")
        return False
    
    print(f"✅ Success: Batch updated {updated_count} configurations")
    return True


def test_reset_config():
    """Test resetting a configuration to default."""
    print("\n🔄 Testing: Reset configuration...")
    
    # Update to non-default value first
    requests.put(
        f"{API_URL}/admin/config/system/summary_threshold",
        json={"value": "12000"}
    )
    
    # Reset to default
    response = requests.post(f"{API_URL}/admin/config/system/summary_threshold/reset")
    
    if response.status_code != 200:
        print(f"❌ Failed: HTTP {response.status_code}")
        return False
    
    data = response.json()
    
    if not data.get("success"):
        print(f"❌ Failed: {data.get('message')}")
        return False
    
    config = data.get("config", {})
    if config.get("value") != config.get("default_value"):
        print("❌ Failed: Value not reset to default")
        return False
    
    print(f"✅ Success: Reset to default value {config.get('value')}")
    return True


def test_validation():
    """Test configuration validation."""
    print("\n🔍 Testing: Configuration validation...")
    
    # Try to set value below minimum
    response = requests.put(
        f"{API_URL}/admin/config/system/summary_threshold",
        json={"value": "500"}  # Below min of 1000
    )
    
    if response.status_code == 200:
        print("❌ Failed: Should reject value below minimum")
        return False
    
    print("✅ Success: Validation rejected invalid value")
    return True


def test_frontend_page():
    """Test frontend page accessibility."""
    print("\n🌐 Testing: Frontend page accessibility...")
    
    response = requests.get(f"{BASE_URL}/system-config.html")
    
    if response.status_code != 200:
        print(f"❌ Failed: HTTP {response.status_code}")
        return False
    
    # Set encoding to handle Chinese characters
    response.encoding = 'utf-8'
    content = response.text
    
    # Check for key elements
    required_elements = [
        "config-",
        "saveConfig",
        "loadConfigs",
        "admin/config/system"
    ]
    
    missing = [elem for elem in required_elements if elem not in content]
    
    if missing:
        print(f"❌ Failed: Missing elements: {missing}")
        return False
    
    print("✅ Success: Frontend page is accessible and contains required elements")
    return True


def test_export_configs():
    """Test exporting configurations."""
    print("\n📤 Testing: Export configurations...")
    
    response = requests.get(f"{API_URL}/admin/config/system/export")
    
    if response.status_code != 200:
        print(f"❌ Failed: HTTP {response.status_code}")
        return False
    
    data = response.json()
    
    if not data.get("success"):
        print(f"❌ Failed: {data.get('message')}")
        return False
    
    configs = data.get("configs", {})
    
    if not configs:
        print("❌ Failed: No configs exported")
        return False
    
    print(f"✅ Success: Exported {len(configs)} configurations")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("🧪 System Configuration Management Tests")
    print("=" * 60)
    
    tests = [
        ("Get All Configs", test_get_all_configs),
        ("Get Config by Category", test_get_config_by_category),
        ("Get Single Config", test_get_single_config),
        ("Update Config", test_update_config),
        ("Batch Update", test_batch_update),
        ("Reset Config", test_reset_config),
        ("Validation", test_validation),
        ("Frontend Page", test_frontend_page),
        ("Export Configs", test_export_configs),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Exception: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
