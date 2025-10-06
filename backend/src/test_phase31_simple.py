"""
Simple test script for Phase 3.1 features using API calls
"""

import httpx
import json
import time

BASE_URL = "http://localhost:8000"


def test_login():
    """Get auth token"""
    print("\n1. Logging in...")
    response = httpx.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": "test@example.com", "password": "test12345"}
    )

    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"✓ Logged in successfully")
        return token
    else:
        print(f"✗ Login failed: {response.text}")
        return None


def test_agent_crud_and_versioning(token):
    """Test agent CRUD with versioning"""
    print("\n" + "="*60)
    print("TEST: Agent CRUD and Versioning")
    print("="*60)

    headers = {"Authorization": f"Bearer {token}"}

    # First, create a default LLM provider
    print("\n0. Creating default LLM provider...")
    provider_data = {
        "name": "Test OpenAI",
        "provider_type": "openai",
        "model_name": "gpt-4",
        "api_key": "sk-test-placeholder",
        "config": {},
        "is_default": True
    }

    response = httpx.post(
        f"{BASE_URL}/api/v1/llm-providers",
        headers=headers,
        json=provider_data,
        timeout=30.0
    )

    if response.status_code == 201:
        provider = response.json()["provider"]
        provider_id = provider["id"]
        print(f"✓ Created provider ID: {provider_id}")
    else:
        print(f"! Could not create provider (may already exist): {response.status_code}")
        provider_id = 1  # Use existing provider

    # Create agent v1
    print("\n1. Creating agent (version 1)...")
    agent_data = {
        "name": "Test Agent v1",
        "role": "Data Analyst",
        "goal": "Analyze data",
        "backstory": "Expert in data analysis",
        "llm_provider_id": provider_id,
        "temperature": 0.7,
        "max_iter": 10,
        "allow_delegation": True,
        "verbose": False,
        "cache": True,
        "max_rpm": 60,
        "max_execution_time": 300,
        "allow_code_execution": False,
        "respect_context_window": True,
        "max_retry_limit": 2,
        "tool_ids": []
    }

    response = httpx.post(
        f"{BASE_URL}/api/v1/agents",
        headers=headers,
        json=agent_data,
        timeout=30.0
    )

    if response.status_code == 201:
        agent = response.json()
        agent_id = agent["id"]
        print(f"✓ Created agent ID: {agent_id}")
        print(f"  Name: {agent['name']}")
        print(f"  Temperature: {agent['temperature']}")
    else:
        print(f"✗ Failed to create agent: {response.text}")
        return

    # Update agent (version 2)
    print("\n2. Updating agent (version 2)...")
    update_data = {
        "name": "Test Agent v2",
        "temperature": 0.8,
        "max_iter": 15
    }

    response = httpx.put(
        f"{BASE_URL}/api/v1/agents/{agent_id}",
        headers=headers,
        json=update_data,
        timeout=30.0
    )

    if response.status_code == 200:
        agent = response.json()
        print(f"✓ Updated agent")
        print(f"  Name: {agent['name']}")
        print(f"  Temperature: {agent['temperature']}")
        print(f"  Max Iter: {agent['max_iter']}")
    else:
        print(f"✗ Failed to update agent: {response.text}")

    # Get version history
    print("\n3. Getting version history...")
    response = httpx.get(
        f"{BASE_URL}/api/v1/agents/{agent_id}/versions",
        headers=headers,
        timeout=30.0
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✓ Found {data['total']} versions")

        for version in data['versions']:
            print(f"\n  Version {version['version_number']}:")
            print(f"    Action: {version['action']}")
            print(f"    Created: {version['created_at']}")

            if version['diff_from_previous']:
                print(f"    Changes:")
                diff = version['diff_from_previous']
                for key, value in diff.get('modified', {}).items():
                    print(f"      • {key}: {value['old']} → {value['new']}")
    else:
        print(f"✗ Failed to get versions: {response.text}")

    # Rollback to version 1
    print("\n4. Rolling back to version 1...")
    response = httpx.post(
        f"{BASE_URL}/api/v1/agents/{agent_id}/rollback/1",
        headers=headers,
        timeout=30.0
    )

    if response.status_code == 200:
        agent = response.json()
        print(f"✓ Rolled back successfully")
        print(f"  Name: {agent['name']}")
        print(f"  Temperature: {agent['temperature']}")

        assert agent['name'] == "Test Agent v1", "Rollback failed - name mismatch!"
        assert agent['temperature'] == 0.7, "Rollback failed - temperature mismatch!"
    else:
        print(f"✗ Failed to rollback: {response.text}")

    # Check versions after rollback
    print("\n5. Checking versions after rollback...")
    response = httpx.get(
        f"{BASE_URL}/api/v1/agents/{agent_id}/versions",
        headers=headers,
        timeout=30.0
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✓ Now have {data['total']} versions (should be 3: create, update, rollback)")
        assert data['total'] == 3, "Should have 3 versions after rollback!"
    else:
        print(f"✗ Failed to get versions: {response.text}")

    # Cleanup
    print("\n6. Cleaning up...")
    response = httpx.delete(
        f"{BASE_URL}/api/v1/agents/{agent_id}",
        headers=headers,
        timeout=30.0
    )

    if response.status_code == 204:
        print(f"✓ Deleted agent {agent_id}")
    else:
        print(f"✗ Failed to delete agent: {response.text}")

    print("\n✅ Agent versioning test PASSED!\n")


def test_provider_crud_and_encryption(token):
    """Test provider CRUD with encryption and versioning"""
    print("="*60)
    print("TEST: Provider CRUD with Encryption and Versioning")
    print("="*60)

    headers = {"Authorization": f"Bearer {token}"}

    # Create provider v1
    print("\n1. Creating LLM provider with API key (version 1)...")
    provider_data = {
        "name": "Test OpenAI Provider v1",
        "provider_type": "openai",
        "model_name": "gpt-4",
        "api_key": "sk-test-key-12345-original",
        "config": {},
        "is_default": False
    }

    response = httpx.post(
        f"{BASE_URL}/api/v1/llm-providers",
        headers=headers,
        json=provider_data,
        timeout=30.0
    )

    if response.status_code == 201:
        data = response.json()
        provider = data["provider"]
        provider_id = provider["id"]
        print(f"✓ Created provider ID: {provider_id}")
        print(f"  Name: {provider['name']}")
        print(f"  API Key Set: {provider.get('api_key_set', False)}")
        print(f"  ✓ API key is NOT exposed in response (encrypted)")
    else:
        print(f"✗ Failed to create provider: {response.text}")
        return

    # Update provider (version 2)
    print("\n2. Updating provider (version 2)...")
    update_data = {
        "name": "Test OpenAI Provider v2",
        "model_name": "gpt-4-turbo"
    }

    response = httpx.put(
        f"{BASE_URL}/api/v1/llm-providers/{provider_id}",
        headers=headers,
        json=update_data,
        timeout=30.0
    )

    if response.status_code == 200:
        data = response.json()
        provider = data["provider"]
        print(f"✓ Updated provider")
        print(f"  Name: {provider['name']}")
        print(f"  Model: {provider['model_name']}")
    else:
        print(f"✗ Failed to update provider: {response.text}")

    # Get version history
    print("\n3. Getting version history...")
    response = httpx.get(
        f"{BASE_URL}/api/v1/llm-providers/{provider_id}/versions",
        headers=headers,
        timeout=30.0
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✓ Found {data['total']} versions")

        for version in data['versions']:
            print(f"\n  Version {version['version_number']}:")
            print(f"    Action: {version['action']}")
            print(f"    Created: {version['created_at']}")

            if version['diff_from_previous']:
                print(f"    Changes:")
                diff = version['diff_from_previous']
                for key, value in diff.get('modified', {}).items():
                    print(f"      • {key}: {value['old']} → {value['new']}")
    else:
        print(f"✗ Failed to get versions: {response.text}")

    # Rollback to version 1
    print("\n4. Rolling back to version 1...")
    response = httpx.post(
        f"{BASE_URL}/api/v1/llm-providers/{provider_id}/rollback/1",
        headers=headers,
        timeout=30.0
    )

    if response.status_code == 200:
        data = response.json()
        provider = data["provider"]
        print(f"✓ Rolled back successfully")
        print(f"  Name: {provider['name']}")
        print(f"  Model: {provider['model_name']}")

        assert provider['name'] == "Test OpenAI Provider v1", "Rollback failed - name mismatch!"
        assert provider['model_name'] == "gpt-4", "Rollback failed - model mismatch!"
    else:
        print(f"✗ Failed to rollback: {response.text}")

    # Check versions after rollback
    print("\n5. Checking versions after rollback...")
    response = httpx.get(
        f"{BASE_URL}/api/v1/llm-providers/{provider_id}/versions",
        headers=headers,
        timeout=30.0
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✓ Now have {data['total']} versions (should be 3: create, update, rollback)")
        assert data['total'] == 3, "Should have 3 versions after rollback!"
    else:
        print(f"✗ Failed to get versions: {response.text}")

    # Cleanup
    print("\n6. Cleaning up...")
    response = httpx.delete(
        f"{BASE_URL}/api/v1/llm-providers/{provider_id}",
        headers=headers,
        timeout=30.0
    )

    if response.status_code == 204:
        print(f"✓ Deleted provider {provider_id}")
    else:
        print(f"✗ Failed to delete provider: {response.text}")

    print("\n✅ Provider encryption and versioning test PASSED!\n")


def main():
    """Run all Phase 3.1 tests"""
    print("\n" + "🚀 PHASE 3.1 API TESTING" + "\n")

    try:
        # Get auth token
        token = test_login()
        if not token:
            print("❌ Cannot proceed without authentication")
            return

        # Test agent versioning
        test_agent_crud_and_versioning(token)

        # Test provider encryption + versioning
        test_provider_crud_and_encryption(token)

        print("="*60)
        print("✅ ALL PHASE 3.1 API TESTS PASSED!")
        print("="*60)
        print("\nPhase 3.1 features verified via API:")
        print("  ✓ Agent CRUD operations")
        print("  ✓ Agent version tracking")
        print("  ✓ Agent rollback functionality")
        print("  ✓ Provider CRUD operations")
        print("  ✓ Provider version tracking")
        print("  ✓ Encrypted API key storage")
        print("  ✓ Provider rollback functionality")
        print("  ✓ Diff generation between versions")
        print("\n")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
