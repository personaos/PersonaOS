#!/usr/bin/env python3
"""
Test script for PersonaOS Web UI setup endpoints
Run this to verify the onboarding API endpoints work correctly.
"""

import requests
import json
import sys
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_CONFIG = {
    "LLM_PROVIDER": "ollama",
    "OLLAMA_MODEL": "openhermes",
    "OLLAMA_API_URL": "",
    "OPENAI_API_KEY": "",
    "ANTHROPIC_API_KEY": "",
    "GOOGLE_API_KEY": "",
    "COHERE_API_KEY": "",
    "PICOVOICE_API_KEY": "",
    "ELEVENLABS_API_KEY": "",
    "MIC_DEVICE_INDEX": "",
    "SPEAKER_DEVICE_INDEX": "",
    "INTENT_ENABLED": "true",
    "SAFETY_LEVEL": "standard",
    "ALLOW_TOOL_EXECUTION": "true",
    "MAX_INTENT_CONFIDENCE": "1.0",
    "DEBUG_MODE": "false",
    "LOG_LEVEL": "INFO",
    "ENABLE_API_LOGGING": "false",
    "WEB_UI_ENABLED": "true",
    "WEB_UI_PORT": "8000",
    "FRONTEND_PORT": "3000"
}

def test_health_endpoint():
    """Test the health endpoint."""
    print("🏥 Testing health endpoint...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['status']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Health check error: {e}")
        return False

def test_setup_defaults():
    """Test the setup defaults endpoint."""
    print("\n📋 Testing setup defaults endpoint...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/setup/defaults", timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            # Check structure
            if "config_sections" in data and "current_values" in data:
                sections = data["config_sections"]
                current_values = data["current_values"]
                
                print(f"✅ Setup defaults retrieved successfully")
                print(f"   📁 Found {len(sections)} configuration sections:")
                for section_name in sections.keys():
                    section_keys = list(sections[section_name].keys())
                    print(f"      - {section_name}: {len(section_keys)} settings")
                
                print(f"   💾 Current values: {len(current_values)} entries")
                
                # Check for sensitive value masking
                sensitive_keys = []
                for section in sections.values():
                    for key, config in section.items():
                        if config.get("sensitive"):
                            sensitive_keys.append(key)
                
                masked_count = 0
                for key in sensitive_keys:
                    value = current_values.get(key, "")
                    if value and "*" in value:
                        masked_count += 1
                
                print(f"   🔒 Sensitive keys found: {len(sensitive_keys)}")
                if masked_count > 0:
                    print(f"   ✅ Masking working: {masked_count} values masked")
                
                return True
            else:
                print("❌ Invalid response structure")
                return False
        else:
            print(f"❌ Setup defaults failed: {response.status_code}")
            print(f"    Response: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Setup defaults error: {e}")
        return False

def test_setup_submit():
    """Test the setup submit endpoint."""
    print("\n💾 Testing setup submit endpoint...")
    try:
        payload = {"config": TEST_CONFIG}
        response = requests.post(
            f"{API_BASE_URL}/api/setup/submit",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print("✅ Setup submit successful")
                print(f"   💾 Configuration saved: {data.get('message')}")
                if data.get("backup_created"):
                    print("   🗂️ Backup created successfully")
                
                # Check if files were created
                env_file = Path("../../.env")
                backup_file = Path("../../.env.backup")
                summary_file = Path("../../onboarding_summary.txt")
                
                if env_file.exists():
                    print("   ✅ .env file created/updated")
                if backup_file.exists():
                    print("   ✅ .env.backup file exists")
                if summary_file.exists():
                    print("   ✅ onboarding_summary.txt created")
                
                return True
            else:
                print(f"❌ Setup submit failed: {data.get('message')}")
                return False
        else:
            print(f"❌ Setup submit failed: {response.status_code}")
            print(f"    Response: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Setup submit error: {e}")
        return False

def test_env_file_content():
    """Verify the .env file was created with correct content."""
    print("\n📄 Testing .env file content...")
    env_file = Path("../../.env")
    
    if not env_file.exists():
        print("❌ .env file not found")
        return False
    
    try:
        content = env_file.read_text()
        
        # Check for key configuration entries
        required_keys = ["LLM_PROVIDER", "OLLAMA_MODEL", "WEB_UI_ENABLED"]
        found_keys = []
        
        for key in required_keys:
            if f"{key}=" in content:
                found_keys.append(key)
        
        if len(found_keys) == len(required_keys):
            print("✅ .env file contains required configuration")
            print(f"   📝 Found keys: {', '.join(found_keys)}")
            return True
        else:
            missing = set(required_keys) - set(found_keys)
            print(f"❌ .env file missing keys: {', '.join(missing)}")
            return False
            
    except Exception as e:
        print(f"❌ Error reading .env file: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 PersonaOS Web UI Setup Endpoint Tests")
    print("=" * 50)
    
    # Check if server is running
    print("🚀 Checking if backend server is running...")
    try:
        requests.get(f"{API_BASE_URL}/", timeout=3)
        print("✅ Backend server is running")
    except requests.exceptions.RequestException:
        print("❌ Backend server not running!")
        print("   Please start it with: cd backend && python main.py")
        sys.exit(1)
    
    # Run tests
    tests = [
        test_health_endpoint,
        test_setup_defaults,
        test_setup_submit,
        test_env_file_content
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    # Results
    print(f"\n🏁 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The onboarding system is working correctly.")
        print("\n💡 Next steps:")
        print("   1. Start the frontend: cd frontend && npm run dev")
        print("   2. Open http://localhost:5173 in your browser")
        print("   3. Complete the onboarding wizard")
    else:
        print("⚠️ Some tests failed. Please check the backend implementation.")
        sys.exit(1)

if __name__ == "__main__":
    main()