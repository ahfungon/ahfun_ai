#!/usr/bin/env python3
"""Test agent registration endpoint."""

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# Test agent registration
print("Testing agent registration...")
response = client.post('/api/agent/register', json={'agent_name': 'Test AI Agent'})
print(f'Status: {response.status_code}')
print(f'Response: {response.json()}')

if response.status_code == 200:
    data = response.json()
    print("\n✅ Registration successful!")
    print(f"Agent ID: {data['agent_id']}")
    print(f"Agent Name: {data['agent_name']}")
    print(f"Auth Token: {data['auth_token']}")
    
    # Test using the token
    print("\n\nTesting authentication with new token...")
    token = data['auth_token']
    response2 = client.get('/api/topic/active', headers={'X-Agent-Token': token})
    print(f'Status: {response2.status_code}')
    if response2.status_code == 404:
        print("✅ Authentication works! (404 is expected - no active topic)")
    else:
        print(f'Response: {response2.json()}')
else:
    print(f"\n❌ Registration failed: {response.json()}")
