#!/usr/bin/env python3
"""Test configuration for Instagram token refresh tests"""

import os

# Test configuration
TEST_CONFIG = {
    # Test Instagram credentials (mock values)
    "IG_ACCESS_TOKEN": "test_access_token_12345",
    "IG_APP_ID": "test_app_id_12345",
    "IG_APP_SECRET": "test_app_secret_12345",
    "IG_USER_ID": "test_user_id_12345",
    
    # Test file paths
    "TOKEN_FILE": "test_instagram_token.json",
    "TEST_DATA_DIR": "test_data",
    
    # Performance test settings
    "PERFORMANCE_THRESHOLDS": {
        "max_token_load_time": 0.1,  # seconds
        "max_token_save_time": 0.1,  # seconds
        "max_api_request_time": 1.0,  # seconds
        "max_large_response_time": 2.0,  # seconds
    },
    
    # Test data
    "MOCK_TOKEN_DATA": {
        "access_token": "mock_token_12345",
        "expires_in": 3600,
        "token_type": "bearer",
        "refreshed_at": "2024-01-01T00:00:00"
    },
    
    "MOCK_INSTAGRAM_RESPONSE": {
        "business_discovery": {
            "profile_picture_url": "https://example.com/test_pic.jpg",
            "biography": "Test hair stylist profile"
        }
    }
}

def get_test_config():
    """Get test configuration"""
    return TEST_CONFIG

def setup_test_environment():
    """Set up test environment"""
    # Create test data directory if it doesn't exist
    os.makedirs(TEST_CONFIG["TEST_DATA_DIR"], exist_ok=True)
    
    # Set test environment variables
    os.environ["IG_ACCESS_TOKEN"] = TEST_CONFIG["IG_ACCESS_TOKEN"]
    os.environ["IG_APP_ID"] = TEST_CONFIG["IG_APP_ID"]
    os.environ["IG_APP_SECRET"] = TEST_CONFIG["IG_APP_SECRET"]
    os.environ["IG_USER_ID"] = TEST_CONFIG["IG_USER_ID"]

def cleanup_test_environment():
    """Clean up test environment"""
    # Remove test files
    test_files = [
        TEST_CONFIG["TOKEN_FILE"],
        "instagram_token.json"
    ]
    
    for file_path in test_files:
        if os.path.exists(file_path):
            os.remove(file_path)
    
    # Remove test data directory
    if os.path.exists(TEST_CONFIG["TEST_DATA_DIR"]):
        import shutil
        shutil.rmtree(TEST_CONFIG["TEST_DATA_DIR"])
