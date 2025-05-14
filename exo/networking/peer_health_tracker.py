import time
from typing import Dict, Optional
from exo.helpers import DEBUG

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
        self.failure_counts: Dict[str, int] = {}
        self.unhealthy_until: Dict[str, float] = {}
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
            if DEBUG >= 2:
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
                if DEBUG >= 2:
                    print(f"Peer {peer_id} cooldown period expired, marking as healthy again")
                return True
            return False
        return True
    
    def get_cooldown_remaining(self, peer_id: str) -> Optional[float]:
        """
        Get the remaining cooldown time for an unhealthy peer.
        
        Args:
            peer_id: The ID of the peer to check
            
        Returns:
            The remaining cooldown time in seconds, or None if the peer is healthy
        """
        if peer_id in self.unhealthy_until:
            remaining = self.unhealthy_until[peer_id] - time.time()
            if remaining > 0:
                return remaining
        return None
