#!/usr/bin/env python3
"""
Standalone test script for the circuit breaker pattern.
This doesn't depend on the exo module.
"""

import asyncio
import time

class PeerHealthTracker:
    """
    Tracks the health of peers and provides circuit-breaking functionality.
    
    This class keeps track of peer failures and temporarily disables sending
    to peers that are experiencing issues, implementing a simple circuit breaker pattern.
    """
    
    def __init__(self, failure_threshold: int = 3, cooldown_period: int = 60):
        """
        Initialize the PeerHealthTracker.
        
        Args:
            failure_threshold: Number of consecutive failures before marking a peer as unhealthy
            cooldown_period: Time in seconds to wait before trying the peer again
        """
        self.failure_counts = {}
        self.unhealthy_until = {}
        self.failure_threshold = failure_threshold
        self.cooldown_period = cooldown_period
    
    def record_failure(self, peer_id: str) -> None:
        """
        Record a failure for a peer.
        
        If the number of consecutive failures exceeds the threshold,
        the peer will be marked as unhealthy for the cooldown period.
        
        Args:
            peer_id: The ID of the peer that experienced a failure
        """
        if peer_id not in self.failure_counts:
            self.failure_counts[peer_id] = 0
        
        self.failure_counts[peer_id] += 1
        
        if self.failure_counts[peer_id] >= self.failure_threshold:
            print(f"Marking peer {peer_id} as unhealthy for {self.cooldown_period} seconds after {self.failure_counts[peer_id]} consecutive failures")
            self.unhealthy_until[peer_id] = time.time() + self.cooldown_period
            self.failure_counts[peer_id] = 0
    
    def record_success(self, peer_id: str) -> None:
        """
        Record a successful operation for a peer.
        
        This resets the failure count for the peer.
        
        Args:
            peer_id: The ID of the peer that had a successful operation
        """
        if peer_id in self.failure_counts:
            self.failure_counts[peer_id] = 0
    
    def is_healthy(self, peer_id: str) -> bool:
        """
        Check if a peer is considered healthy.
        
        A peer is unhealthy if it has been marked as such and the cooldown period
        has not yet expired.
        
        Args:
            peer_id: The ID of the peer to check
            
        Returns:
            True if the peer is healthy, False otherwise
        """
        if peer_id in self.unhealthy_until:
            if time.time() > self.unhealthy_until[peer_id]:
                # Cooldown period has expired, remove from unhealthy list
                del self.unhealthy_until[peer_id]
                print(f"Peer {peer_id} cooldown period expired, marking as healthy again")
                return True
            return False
        return True

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
