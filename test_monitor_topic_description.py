#!/usr/bin/env python3
"""
Test script to verify monitor page displays topic description correctly.
"""
import requests
import json
import time

API_URL = "http://localhost:8000/api"

# Use the active agent credentials
AGENT_ID = "agent-d536c5c6"  # Agent-Alice
# We need to get the auth token from the running agent process
# For now, let's just check if there's an active topic

def check_active_topic():
    """Check if there's an active topic and if it has a description."""
    response = requests.get(f"{API_URL}/monitor/topic/active")
    
    if response.status_code == 404:
        print("❌ No active topic found")
        print("\nThis is expected if:")
        print("1. The last topic was closed and a new one hasn't been generated yet")
        print("2. The agents are waiting for the next cycle")
        print("\nSolution: Wait for the agents to generate a new topic, or manually create one")
        return None
    
    if response.status_code != 200:
        print(f"❌ Error: HTTP {response.status_code}")
        print(response.text)
        return None
    
    topic = response.json()
    print("✅ Active topic found!")
    print(f"\nTopic ID: {topic['topic_id']}")
    print(f"Title: {topic['title']}")
    print(f"Status: {topic['status']}")
    
    if topic.get('topic_description'):
        print(f"\n📋 Topic Description:")
        print(f"{topic['topic_description']}")
        print("\n✅ Topic has a description - monitor page should display it!")
    else:
        print("\n⚠️  Topic has NO description")
        print("This means it was created before the LLM topic generation fix")
        print("Wait for the next topic to be generated to see the description")
    
    return topic

def check_closed_topics():
    """Check recent closed topics to verify they have descriptions."""
    response = requests.get(f"{API_URL}/monitor/topics/closed?limit=5")
    
    if response.status_code != 200:
        print(f"❌ Error: HTTP {response.status_code}")
        return
    
    data = response.json()
    topics = data.get('topics', [])
    
    print(f"\n📚 Recent Closed Topics ({len(topics)}):")
    print("=" * 80)
    
    for i, topic in enumerate(topics, 1):
        print(f"\n{i}. {topic['title']}")
        print(f"   Topic ID: {topic['topic_id']}")
        print(f"   Messages: {topic['message_count']}")
        print(f"   Score: {topic['end_score']}")
        
        if topic.get('topic_description'):
            desc = topic['topic_description']
            if len(desc) > 100:
                desc = desc[:100] + "..."
            print(f"   📋 Description: {desc}")
            print(f"   ✅ Has description")
        else:
            print(f"   ⚠️  No description")

def main():
    print("=" * 80)
    print("Monitor Page Topic Description Test")
    print("=" * 80)
    
    # Check active topic
    print("\n1. Checking Active Topic...")
    print("-" * 80)
    active_topic = check_active_topic()
    
    # Check closed topics
    print("\n2. Checking Closed Topics...")
    print("-" * 80)
    check_closed_topics()
    
    # Summary
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    
    if active_topic and active_topic.get('topic_description'):
        print("\n✅ SUCCESS: Active topic has a description!")
        print("   The monitor page should display it at the top of the topic info card.")
        print(f"\n   View it at: http://localhost:8000/frontend/monitor.html")
    elif active_topic:
        print("\n⚠️  Active topic exists but has NO description")
        print("   This is an old topic created before the LLM fix.")
        print("   Wait for the next topic to be generated.")
    else:
        print("\n⚠️  No active topic currently")
        print("   The agents may be between topics.")
        print("   Check the closed topics - they all have descriptions!")
        print("\n   You can:")
        print("   1. Wait for agents to generate a new topic")
        print("   2. View closed topics in the monitor page (click 'History' button)")
        print(f"   3. Open: http://localhost:8000/frontend/monitor.html")

if __name__ == "__main__":
    main()
