"""
Resource display for exo nodes.
Integrates with the Rich UI framework to display resource usage information.
"""

import sys
import time
from typing import Dict, List, Optional, Tuple
import asyncio
from exo import DEBUG

try:
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

class ResourceDisplay:
    """
    A class to display resource usage information.
    Integrates with the Rich UI framework when available.
    """

    def __init__(self):
        self.node_resources: Dict[str, Dict] = {}
        self.last_update_time = 0
        self.update_interval = 1.0  # Update at most every 1 second
        self.is_tty = sys.stdout.isatty()  # Check if stdout is a terminal
        self.local_node_id = None
        self.display_enabled = True
        self.topology_viz = None

    def set_local_node_id(self, node_id: str) -> None:
        """Set the ID of the local node."""
        self.local_node_id = node_id

    def set_topology_viz(self, topology_viz) -> None:
        """Set the topology visualization object."""
        self.topology_viz = topology_viz

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
        """Disable the resource display."""
        self.display_enabled = False

    def _update_display(self) -> None:
        """Update the resource display."""
        if not self.display_enabled or not self.node_resources:
            return

        # If we have a topology visualization, update it
        if self.topology_viz:
            self.topology_viz.update_resource_display(self.node_resources, self.local_node_id)

    def get_resource_panel(self) -> Optional[Panel]:
        """
        Get a Rich panel containing resource usage information.

        Returns:
            A Rich Panel object or None if Rich is not available
        """
        if not RICH_AVAILABLE or not self.node_resources:
            return None

        from exo.monitoring.resource_monitor import resource_monitor

        # Create a table for resource information
        table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
        table.add_column("Node", style="bright_green")
        table.add_column("RAM", style="cyan")
        table.add_column("GPU", style="magenta")

        # Sort nodes to put local node first, then alphabetically
        sorted_nodes = sorted(
            self.node_resources.keys(),
            key=lambda node_id: (node_id != self.local_node_id, node_id)
        )

        for node_id in sorted_nodes:
            resource_data = self.node_resources[node_id]
            is_local = node_id == self.local_node_id

            if not resource_data or "ram" not in resource_data or "gpu" not in resource_data:
                continue

            # Format node ID with indicator for local node
            node_text = Text(f"{'* ' if is_local else '  '}Node {node_id[:8]}")
            if is_local:
                node_text.stylize("bold bright_green")

            # Format RAM usage
            ram = resource_data["ram"]
            ram_text = Text(f"RAM: {ram['used'] / (1024**3):.1f}GB/{ram['total'] / (1024**3):.1f}GB ({ram['percent']}%)")

            # Format GPU usage
            gpu = resource_data["gpu"]
            if gpu.get("available", False):
                gpu_text = Text(f"GPU: {gpu.get('used_memory', 0) / (1024**3):.1f}GB/{gpu.get('total_memory', 0) / (1024**3):.1f}GB ({gpu.get('memory_percent', 0)}%)")
                if "utilization" in gpu:
                    gpu_text.append(f", Util: {gpu['utilization']}%")
            else:
                gpu_text = Text("GPU: Not available")

            table.add_row(node_text, ram_text, gpu_text)

        return Panel(table, title="Resource Usage", border_style="green")

    def get_resource_text(self) -> List[Tuple[str, str]]:
        """
        Get resource usage as text for embedding in other displays.

        Returns:
            List of (node_id, formatted_text) tuples
        """
        from exo.monitoring.resource_monitor import resource_monitor

        result = []

        # Sort nodes to put local node first, then alphabetically
        sorted_nodes = sorted(
            self.node_resources.keys(),
            key=lambda node_id: (node_id != self.local_node_id, node_id)
        )

        for node_id in sorted_nodes:
            resource_data = self.node_resources[node_id]
            is_local = node_id == self.local_node_id

            # Format the resource information
            text = resource_monitor.format_resource_usage(resource_data, node_id, is_local)
            result.append((node_id, text))

        return result

    def clear(self) -> None:
        """Clear the resource display and reset the state."""
        self.node_resources = {}


# Singleton instance
resource_display = ResourceDisplay()
