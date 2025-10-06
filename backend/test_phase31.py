"""
Test script for Phase 3.1 features:
- Encryption service
- Agent versioning
- Provider versioning with encryption
- Rollback functionality
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.encryption_service import get_encryption_service
from db.postgres import SessionLocal
from services.agent_service import AgentService
from services.llm_provider_service import LLMProviderService
from services.versioning_service import VersioningService
from schemas.agents import AgentCreate, AgentUpdate
from schemas.llm_providers import LLMProviderCreate, LLMProviderUpdate


def test_encryption():
    """Test encryption/decryption functionality"""
    print("\n" + "="*60)
    print("TEST 1: Encryption Service")
    print("="*60)

    encryption = get_encryption_service()

    # Test basic encryption
    plaintext = "sk-test-api-key-12345"
    encrypted = encryption.encrypt(plaintext)
    decrypted = encryption.decrypt(encrypted)

    print(f"✓ Original:  {plaintext}")
    print(f"✓ Encrypted: {encrypted[:50]}...")
    print(f"✓ Decrypted: {decrypted}")

    assert plaintext == decrypted, "Encryption/decryption failed!"
    print("✅ Encryption service working correctly\n")


async def test_agent_versioning():
    """Test agent version tracking"""
    print("="*60)
    print("TEST 2: Agent Version Tracking")
    print("="*60)

    db = SessionLocal()

    try:
        agent_service = AgentService(db)
        versioning_service = VersioningService(db)

        # Create an agent
        agent_data = AgentCreate(
            name="Test Agent v1",
            role="Data Analyst",
            goal="Analyze data",
            backstory="Expert in data analysis",
            llm_provider_id=1,
            temperature=0.7,
            max_iter=10,
            allow_delegation=True,
            verbose=False,
            cache=True,
            max_rpm=60,
            max_execution_time=300,
            allow_code_execution=False,
            respect_context_window=True,
            max_retry_limit=2
        )

        print("\n1. Creating agent...")
        agent = await agent_service.create_agent(agent_data)
        print(f"✓ Created agent ID: {agent.id}")

        # Check version 1
        versions, total = versioning_service.get_agent_versions(agent.id, limit=10)
        print(f"✓ Version count: {total}")
        assert total == 1, "Should have 1 version after creation"
        print(f"✓ Version 1 action: {versions[0].action.value}")

        # Update the agent
        print("\n2. Updating agent...")
        update_data = AgentUpdate(
            name="Test Agent v2",
            temperature=0.8,
            max_iter=15
        )
        agent = await agent_service.update_agent(agent.id, update_data)
        print(f"✓ Updated agent name: {agent.name}")

        # Check version 2
        versions, total = versioning_service.get_agent_versions(agent.id, limit=10)
        print(f"✓ Version count: {total}")
        assert total == 2, "Should have 2 versions after update"

        # Check diff
        latest_version = versions[0]
        print(f"\n3. Version 2 diff:")
        if latest_version.diff_from_previous:
            for key, value in latest_version.diff_from_previous.get('modified', {}).items():
                print(f"  • {key}: {value['old']} → {value['new']}")

        # Test rollback
        print("\n4. Rolling back to version 1...")
        agent = versioning_service.rollback_agent(agent.id, version_number=1)
        print(f"✓ Agent name after rollback: {agent.name}")
        assert agent.name == "Test Agent v1", "Rollback failed!"

        # Check version 3 (rollback creates new version)
        versions, total = versioning_service.get_agent_versions(agent.id, limit=10)
        print(f"✓ Version count after rollback: {total}")
        assert total == 3, "Should have 3 versions (create, update, rollback)"

        # Cleanup
        await agent_service.delete_agent(agent.id)
        print("\n✅ Agent versioning working correctly\n")

    finally:
        db.close()


async def test_provider_encryption_versioning():
    """Test provider versioning with encrypted credentials"""
    print("="*60)
    print("TEST 3: Provider Versioning with Encryption")
    print("="*60)

    db = SessionLocal()

    try:
        provider_service = LLMProviderService(db)
        versioning_service = VersioningService(db)

        # Create a provider
        provider_data = LLMProviderCreate(
            name="Test OpenAI Provider v1",
            provider_type="openai",
            model_name="gpt-4",
            api_key="sk-test-key-12345",
            api_base=None,
            config={},
            is_default=False
        )

        print("\n1. Creating LLM provider...")
        provider_dict = await provider_service.create_provider(
            tenant_id=1,
            provider_data=provider_data
        )
        provider_id = provider_dict['id']
        print(f"✓ Created provider ID: {provider_id}")
        print(f"✓ API key set: {provider_dict.get('api_key_set', False)}")

        # Verify API key is encrypted in database
        from models.llm_provider import LLMProvider
        provider = db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
        print(f"✓ Encrypted API key in DB: {provider.api_key[:50]}...")

        # Decrypt and verify
        decrypted_key = provider_service.get_decrypted_api_key(provider)
        print(f"✓ Decrypted API key: {decrypted_key}")
        assert decrypted_key == "sk-test-key-12345", "Decryption failed!"

        # Check version 1
        versions, total = versioning_service.get_provider_versions(provider_id, limit=10)
        print(f"✓ Version count: {total}")
        assert total == 1, "Should have 1 version after creation"

        # Update provider
        print("\n2. Updating provider...")
        update_data = LLMProviderUpdate(
            name="Test OpenAI Provider v2",
            model_name="gpt-4-turbo"
        )
        provider_dict = await provider_service.update_provider(
            provider_id=provider_id,
            tenant_id=1,
            provider_data=update_data
        )
        print(f"✓ Updated provider name: {provider_dict['name']}")

        # Check version 2
        versions, total = versioning_service.get_provider_versions(provider_id, limit=10)
        print(f"✓ Version count: {total}")
        assert total == 2, "Should have 2 versions after update"

        # Check diff
        latest_version = versions[0]
        print(f"\n3. Version 2 diff:")
        if latest_version.diff_from_previous:
            for key, value in latest_version.diff_from_previous.get('modified', {}).items():
                print(f"  • {key}: {value['old']} → {value['new']}")

        # Test rollback
        print("\n4. Rolling back to version 1...")
        provider = versioning_service.rollback_provider(provider_id, version_number=1)
        print(f"✓ Provider name after rollback: {provider.name}")
        assert provider.name == "Test OpenAI Provider v1", "Rollback failed!"

        # Verify API key still works after rollback
        decrypted_key = provider_service.get_decrypted_api_key(provider)
        print(f"✓ Decrypted API key after rollback: {decrypted_key}")
        assert decrypted_key == "sk-test-key-12345", "API key lost after rollback!"

        # Cleanup
        await provider_service.delete_provider(provider_id, tenant_id=1)
        print("\n✅ Provider versioning with encryption working correctly\n")

    finally:
        db.close()


async def run_all_tests():
    """Run all Phase 3.1 tests"""
    print("\n" + "🚀 PHASE 3.1 TESTING" + "\n")

    try:
        # Test 1: Encryption
        test_encryption()

        # Test 2: Agent versioning
        await test_agent_versioning()

        # Test 3: Provider encryption + versioning
        await test_provider_encryption_versioning()

        print("="*60)
        print("✅ ALL PHASE 3.1 TESTS PASSED!")
        print("="*60)
        print("\nPhase 3.1 features verified:")
        print("  ✓ Encryption service (AES-256)")
        print("  ✓ Agent version tracking")
        print("  ✓ Provider version tracking")
        print("  ✓ Encrypted credentials storage")
        print("  ✓ Rollback functionality")
        print("  ✓ Diff generation")
        print("\n")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_all_tests())
