#!/usr/bin/env python3
"""
Test script to verify the PeerHealthTracker implementation.
Run this script to see how the circuit breaker pattern works.
"""

import asyncio
import time
from exo.networking.peer_health_tracker import PeerHealthTracker

async def test_peer_health_tracker():
    # Create a health tracker with a low threshold for testing
    tracker = PeerHealthTracker(failure_threshold=2, cooldown_period=5)
    
    # Test basic functionality
    print("Testing basic functionality...")
    peer_id = "test-peer-1"
    
    # Should be healthy initially
    assert tracker.is_healthy(peer_id), "Peer should be healthy initially"
    print(f"Peer {peer_id} is healthy: {tracker.is_healthy(peer_id)}")
    
    # Record a failure
    tracker.record_failure(peer_id)
    assert tracker.is_healthy(peer_id), "Peer should still be healthy after one failure"
    print(f"After 1 failure, peer {peer_id} is healthy: {tracker.is_healthy(peer_id)}")
    
    # Record another failure to trigger the circuit breaker
    tracker.record_failure(peer_id)
    assert not tracker.is_healthy(peer_id), "Peer should be unhealthy after threshold failures"
    print(f"After 2 failures, peer {peer_id} is healthy: {tracker.is_healthy(peer_id)}")
    
    # Check cooldown
    print(f"Waiting for cooldown period ({tracker.cooldown_period} seconds)...")
    await asyncio.sleep(tracker.cooldown_period + 0.1)
    assert tracker.is_healthy(peer_id), "Peer should be healthy again after cooldown"
    print(f"After cooldown, peer {peer_id} is healthy: {tracker.is_healthy(peer_id)}")
    
    # Test success resets failure count
    print("\nTesting that success resets failure count...")
    peer_id = "test-peer-2"
    
    # Record a failure
    tracker.record_failure(peer_id)
    assert tracker.is_healthy(peer_id), "Peer should still be healthy after one failure"
    print(f"After 1 failure, peer {peer_id} is healthy: {tracker.is_healthy(peer_id)}")
    
    # Record a success
    tracker.record_success(peer_id)
    assert tracker.is_healthy(peer_id), "Peer should be healthy after success"
    print(f"After success, peer {peer_id} is healthy: {tracker.is_healthy(peer_id)}")
    
    # Record a failure again
    tracker.record_failure(peer_id)
    assert tracker.is_healthy(peer_id), "Peer should still be healthy after one failure (counter was reset)"
    print(f"After another failure, peer {peer_id} is healthy: {tracker.is_healthy(peer_id)}")
    
    print("\nAll tests passed!")

if __name__ == "__main__":
    asyncio.run(test_peer_health_tracker())
