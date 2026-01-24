#!/usr/bin/env python3
"""
Test script for AiChatCfgManager refactoring
Tests the callback mechanism without Qt dependencies
"""

# Mock the database functions for testing
class MockRecord:
    def __init__(self):
        self.current_position = "[116, 39]"
        self.last_position = "[115, 38]"
        self.life_point = 100
        self.energy_point = 100
        self.money = 1000
        self.profession = "Developer"
        self.sign = "Test"

def mock_query_AiChatCfg_map():
    return MockRecord()

def mock_update_AiChatCfg_map(**kwargs):
    print(f"Mock update called with: {kwargs}")

# Patch the imports
import sys
from unittest.mock import MagicMock

# Create mock modules
db_factory_mock = MagicMock()
db_factory_mock.query_AiChatCfg_map = mock_query_AiChatCfg_map
db_factory_mock.update_AiChatCfg_map = mock_update_AiChatCfg_map
db_factory_mock.query_AiChatCfg_map_setting = mock_query_AiChatCfg_map
db_factory_mock.update_AiChatCfg_by_user_id = mock_update_AiChatCfg_map

sys.modules['db.DBFactory'] = db_factory_mock
sys.modules['util'] = MagicMock()
sys.modules['i18n'] = MagicMock()

# Now we can test the AiChatCfgManager
class TestAiChatCfgManager:
    def __init__(self):
        self.callback_called = False
        self.callback_property = None

    def test_callback(self, property_name):
        """Test callback function"""
        print(f"✓ Callback triggered for property: {property_name}")
        self.callback_called = True
        self.callback_property = property_name

    def run_tests(self):
        print("=" * 60)
        print("Testing AiChatCfgManager Refactoring")
        print("=" * 60)

        # Import after mocking
        from backend.modules.sns.ai_social_engine_adapter import AiChatCfgManager

        # Test 1: Create instance
        print("\n[Test 1] Creating AiChatCfgManager instance...")
        manager = AiChatCfgManager()
        print("✓ Instance created successfully")

        # Test 2: Connect callback
        print("\n[Test 2] Connecting callback...")
        manager.connect(self.test_callback)
        print("✓ Callback connected")

        # Test 3: Read property
        print("\n[Test 3] Reading property...")
        try:
            life_point = manager.life_point
            print(f"✓ Read life_point: {life_point}")
        except Exception as e:
            print(f"✗ Error reading property: {e}")

        # Test 4: Update property (should trigger callback)
        print("\n[Test 4] Updating property (should trigger callback)...")
        self.callback_called = False
        try:
            manager.money = 2000
            if self.callback_called and self.callback_property == "money":
                print("✓ Property update triggered callback correctly")
            else:
                print("✗ Callback not triggered or wrong property")
        except Exception as e:
            print(f"✗ Error updating property: {e}")

        # Test 5: Multiple callbacks
        print("\n[Test 5] Testing multiple callbacks...")
        callback_count = [0]

        def second_callback(prop):
            callback_count[0] += 1
            print(f"  Second callback triggered for: {prop}")

        manager.connect(second_callback)
        self.callback_called = False
        manager.energy_point = 90

        if self.callback_called and callback_count[0] == 1:
            print("✓ Multiple callbacks work correctly")
        else:
            print("✗ Multiple callbacks failed")

        # Test 6: Disconnect callback
        print("\n[Test 6] Testing disconnect...")
        manager.disconnect(second_callback)
        callback_count[0] = 0
        manager.life_point = 95

        if callback_count[0] == 0:
            print("✓ Disconnect works correctly")
        else:
            print("✗ Disconnect failed")

        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)

if __name__ == "__main__":
    tester = TestAiChatCfgManager()
    tester.run_tests()
