"""
Terminal display for resource usage information.
Provides a clean, non-flickering display of resource usage for all nodes.
"""

import sys
import time
from typing import Dict, List, Optional
import asyncio
from exo import DEBUG

class ResourceDisplay:
    """
    A class to display resource usage in the terminal without flickering.
    Uses ANSI escape codes to update a section of the terminal.
    """
    
    def __init__(self):
        self.node_resources: Dict[str, Dict] = {}
        self.last_update_time = 0
        self.update_interval = 1.0  # Update at most every 1 second
        self.last_display_lines = 0
        self.is_tty = sys.stdout.isatty()  # Check if stdout is a terminal
        self.local_node_id = None
        self.display_enabled = True
        self.display_position = "bottom"  # Can be "top" or "bottom"
        
    def set_local_node_id(self, node_id: str) -> None:
        """Set the ID of the local node."""
        self.local_node_id = node_id
    
    def update(self, node_id: str, resource_data: Dict) -> None:
        """
        Update the resource data for a specific node.
        
        Args:
            node_id: The ID of the node
            resource_data: Resource usage data for the node
        """
        # Store the resource data
        self.node_resources[node_id] = resource_data
        
        # Update the display if enough time has passed
        current_time = time.time()
        if current_time - self.last_update_time >= self.update_interval:
            self.last_update_time = current_time
            self._update_display()
    
    def enable(self) -> None:
        """Enable the resource display."""
        self.display_enabled = True
        self._update_display()
    
    def disable(self) -> None:
        """Disable the resource display and clear it from the terminal."""
        self.display_enabled = False
        self._clear_display()
    
    def set_display_position(self, position: str) -> None:
        """
        Set the position of the resource display in the terminal.
        
        Args:
            position: Either "top" or "bottom"
        """
        if position in ["top", "bottom"]:
            self.display_position = position
            self._update_display()
    
    def _update_display(self) -> None:
        """Update the resource display in the terminal."""
        if not self.is_tty or not self.display_enabled or not self.node_resources:
            return
        
        # Clear the previous display
        self._clear_display()
        
        # Format the resource information
        lines = self._format_resource_info()
        
        # Display the resource information
        if self.display_position == "bottom":
            # Save cursor position
            sys.stdout.write("\033[s")
            
            # Move to the bottom of the terminal
            sys.stdout.write(f"\033[{len(lines) + 1}B")
            
            # Print the resource information
            for line in lines:
                sys.stdout.write(f"\033[2K{line}\n")
            
            # Restore cursor position
            sys.stdout.write("\033[u")
        else:  # top position
            # Print the resource information at the current position
            for line in lines:
                sys.stdout.write(f"{line}\n")
        
        sys.stdout.flush()
        self.last_display_lines = len(lines)
    
    def _clear_display(self) -> None:
        """Clear the resource display from the terminal."""
        if not self.is_tty or self.last_display_lines == 0:
            return
        
        if self.display_position == "bottom":
            # Save cursor position
            sys.stdout.write("\033[s")
            
            # Move to the bottom of the terminal
            sys.stdout.write(f"\033[{self.last_display_lines + 1}B")
            
            # Clear the lines
            for _ in range(self.last_display_lines):
                sys.stdout.write("\033[2K\033[1A")
            sys.stdout.write("\033[2K")
            
            # Restore cursor position
            sys.stdout.write("\033[u")
        else:  # top position
            # Move to the beginning of the line and clear the previous lines
            for _ in range(self.last_display_lines):
                sys.stdout.write("\033[2K\033[1A")
            sys.stdout.write("\033[2K")
        
        sys.stdout.flush()
    
    def _format_resource_info(self) -> List[str]:
        """
        Format the resource information for display.
        
        Returns:
            List of formatted lines
        """
        from exo.monitoring.resource_monitor import resource_monitor
        
        lines = ["=== Resource Usage ==="]
        
        # Sort nodes to put local node first, then alphabetically
        sorted_nodes = sorted(
            self.node_resources.keys(),
            key=lambda node_id: (node_id != self.local_node_id, node_id)
        )
        
        for node_id in sorted_nodes:
            resource_data = self.node_resources[node_id]
            is_local = node_id == self.local_node_id
            
            # Format the resource information
            line = resource_monitor.format_resource_usage(resource_data, node_id, is_local)
            lines.append(line)
        
        return lines
    
    def clear(self) -> None:
        """Clear the resource display and reset the state."""
        self._clear_display()
        self.node_resources = {}
        self.last_display_lines = 0


# Singleton instance
resource_display = ResourceDisplay()
