"""
Console progress display for model downloads.
This module provides a clean, non-flickering progress display for the terminal.
"""

import sys
import time
from typing import Dict, Optional
from datetime import timedelta
from exo.helpers import pretty_print_bytes, pretty_print_bytes_per_second
from exo.download.download_progress import RepoProgressEvent
from exo.inference.shard import Shard


class ConsoleProgressDisplay:
    """
    A class to display download progress in the console without flickering.
    Uses ANSI escape codes to update a single line instead of printing multiple lines.
    """

    def __init__(self):
        self.active_downloads: Dict[str, RepoProgressEvent] = {}
        self.last_update_time = 0
        self.update_interval = 0.5  # Update at most every 0.5 seconds
        self.last_line_length = 0
        self.is_tty = sys.stdout.isatty()  # Check if stdout is a terminal

    def update(self, shard: Shard, event: RepoProgressEvent) -> None:
        """
        Update the progress display for a specific shard.

        Args:
            shard: The shard being downloaded
            event: The progress event containing download information
        """
        current_time = time.time()

        # Store the event
        self.active_downloads[shard.model_id] = event

        # Only update the display at most every update_interval seconds
        if current_time - self.last_update_time < self.update_interval:
            return

        self.last_update_time = current_time

        # Only display progress if stdout is a terminal
        if not self.is_tty:
            return

        # Display the progress
        self._display_progress()

    def _display_progress(self) -> None:
        """Display the current download progress."""
        if not self.active_downloads:
            return

        # Clear any completed downloads
        completed_downloads = []
        for model_id, event in list(self.active_downloads.items()):
            if event.status == "complete":
                completed_downloads.append(model_id)

        # Remove completed downloads
        for model_id in completed_downloads:
            del self.active_downloads[model_id]

        # If we just completed some downloads, print a completion message
        if completed_downloads and self.is_tty:
            self._clear_line()
            for model_id in completed_downloads:
                print(f"✓ Download complete: {model_id}")

        if not self.active_downloads:
            # Clear the last line if all downloads are complete
            self._clear_line()
            return

        # Get the most active download (the one with the highest speed)
        active_model_id = max(
            self.active_downloads.keys(),
            key=lambda k: self.active_downloads[k].overall_speed
        )
        event = self.active_downloads[active_model_id]

        # Create the progress line
        progress_line = self._format_progress_line(active_model_id, event)

        # Display the progress
        self._print_progress(progress_line)

    def _format_progress_line(self, model_id: str, event: RepoProgressEvent) -> str:
        """Format a progress line for display."""
        # Calculate percentage
        percentage = (event.downloaded_bytes / event.total_bytes * 100) if event.total_bytes > 0 else 0

        # Format the progress bar
        bar_width = 30
        filled_width = int(percentage / 100 * bar_width)
        bar = f"[{'=' * filled_width}{' ' * (bar_width - filled_width)}]"

        # Format the progress information
        progress_info = (
            f"Downloading {model_id}: {percentage:.1f}% "
            f"{bar} "
            f"{pretty_print_bytes(event.downloaded_bytes)}/{pretty_print_bytes(event.total_bytes)} "
            f"({pretty_print_bytes_per_second(event.overall_speed)}) "
            f"ETA: {self._format_eta(event.overall_eta)}"
        )

        # Add file information if there's an active file
        active_file = next(
            (file_path for file_path, file_progress in event.file_progress.items()
             if file_progress.status == "in_progress"),
            None
        )

        if active_file:
            file_progress = event.file_progress[active_file]
            file_percentage = (file_progress.downloaded / file_progress.total * 100) if file_progress.total > 0 else 0
            progress_info += f" | File: {active_file.split('/')[-1]} ({file_percentage:.1f}%)"

        return progress_info

    def _format_eta(self, eta: timedelta) -> str:
        """Format the ETA in a human-readable format."""
        total_seconds = int(eta.total_seconds())
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    def _print_progress(self, line: str) -> None:
        """Print the progress line, overwriting the previous line."""
        # Clear the previous line
        self._clear_line()

        # Print the new line (without newline)
        sys.stdout.write(line)
        sys.stdout.flush()

        # Store the length of the line
        self.last_line_length = len(line)

    def _clear_line(self) -> None:
        """Clear the current line in the terminal."""
        if self.last_line_length > 0:
            # Move cursor to beginning of line and clear the line
            sys.stdout.write('\r' + ' ' * self.last_line_length + '\r')
            sys.stdout.flush()
            self.last_line_length = 0

    def clear(self) -> None:
        """Clear the progress display."""
        self._clear_line()
        self.active_downloads = {}


# Singleton instance
console_progress = ConsoleProgressDisplay()
