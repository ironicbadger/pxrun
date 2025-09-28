"""Centralized output management for pxrun with rich terminal UI."""

import sys
import time
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from datetime import datetime
import logging

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, ProgressColumn
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich import box
from rich.spinner import Spinner

# Global console instance with max width of 80 columns
console = Console(width=80)

# Suppress all INFO logging by default
logging.getLogger().setLevel(logging.WARNING)


class OutputManager:
    """Manages all terminal output with beautiful formatting."""
    
    def __init__(self):
        self.console = console
        self.quiet_mode = False
        self._live = None
        self._output_buffer = []
        self._buffer_limit = 8
        
    def set_quiet(self, quiet: bool = True):
        """Set quiet mode to reduce output."""
        self.quiet_mode = quiet
        
    def print(self, message: str, style: str = None):
        """Print a message with optional style."""
        if not self.quiet_mode:
            self.console.print(message, style=style)
            
    def success(self, message: str):
        """Print a success message."""
        self.console.print(f"✅ {message}", style="green")
        
    def error(self, message: str):
        """Print an error message."""
        self.console.print(f"❌ {message}", style="red")
        
    def warning(self, message: str):
        """Print a warning message."""
        self.console.print(f"⚠️  {message}", style="yellow")
        
    def info(self, message: str):
        """Print an info message."""
        if not self.quiet_mode:
            self.console.print(f"ℹ️  {message}", style="blue")
            
    def header(self, title: str, subtitle: str = None):
        """Display a header panel."""
        content = Text(title, style="bold")
        if subtitle:
            content.append(f"\n{subtitle}", style="dim")
        panel = Panel(content, box=box.ROUNDED, style="cyan", width=80)
        self.console.print(panel)
        
    def container_config(self, config: Dict[str, Any]):
        """Display container configuration in a nice panel."""
        table = Table(show_header=False, box=None, width=76)  # Leave room for panel borders
        table.add_column("Property", style="cyan", width=12)
        table.add_column("Value", width=60)
        
        # Basic configuration
        table.add_row("Container", f"{config.get('hostname')} (VMID: {config.get('vmid')})")
        table.add_row("Node", config.get('node'))
        table.add_row("Template", config.get('template', '').split('/')[-1].replace('.tar.zst', ''))
        
        # Resources
        table.add_row("CPU Cores", str(config.get('cores')))
        table.add_row("Memory", f"{config.get('memory')} MB")
        table.add_row("Disk", f"{config.get('storage')} GB")
        table.add_row("Storage Pool", config.get('storage_pool'))
        
        # Network
        table.add_row("Network", f"{config.get('network_bridge')} • IP: {config.get('network_ip', 'dhcp')}")
        
        # Provisioning options if present
        if config.get('packages') or config.get('docker') or config.get('tailscale'):
            table.add_row("", "")  # Empty row for separation
            table.add_row("[bold]Provisioning[/bold]", "")
            
            if config.get('packages'):
                packages = config.get('packages', [])
                if len(packages) <= 3:
                    package_str = ", ".join(packages)
                else:
                    package_str = f"{', '.join(packages[:3])}, +{len(packages)-3} more"
                table.add_row("Packages", package_str)
            
            if config.get('docker'):
                table.add_row("Docker", "✓ Will be installed")
            
            if config.get('tailscale'):
                tailscale_info = config.get('tailscale')
                if isinstance(tailscale_info, dict) and tailscale_info.get('tailnet'):
                    table.add_row("Tailscale", f"✓ Will join [bold]{tailscale_info['tailnet']}[/bold]")
                else:
                    table.add_row("Tailscale", "✓ Will be configured")
        
        panel = Panel(table, title="LXC Configuration", box=box.ROUNDED, width=80)
        self.console.print(panel)
        
    @contextmanager
    def spinner(self, text: str, success_text: str = None):
        """Context manager for spinner with automatic success/failure."""
        with self.console.status(text) as status:
            try:
                yield status
                if success_text:
                    self.success(success_text)
            except Exception as e:
                self.error(f"Failed: {str(e)}")
                raise
                
    @contextmanager
    def progress_task(self, description: str, total: int = None):
        """Context manager for a progress bar task."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task(description, total=total or 100)
            
            def update(advance: int = 1, description: str = None):
                if description:
                    progress.update(task, description=description)
                progress.update(task, advance=advance)
                
            yield update
            progress.update(task, completed=total or 100)
            
    @contextmanager  
    def live_output(self, title: str):
        """Context manager for live streaming output display."""
        self._output_buffer = []
        self._current_title = title
        
        def generate_display():
            # Create output panel with buffer content
            if self._output_buffer:
                # Show last N lines
                visible_lines = self._output_buffer[-self._buffer_limit:]
                content = "\n".join(visible_lines)
            else:
                content = "[dim italic]Starting...[/dim italic]"
                
            return Panel(
                content,
                title=f"[bold cyan]{self._current_title}[/bold cyan]",
                box=box.ROUNDED,
                padding=(0, 1),
                width=80
            )
            
        with Live(generate_display(), console=self.console, refresh_per_second=10, transient=True) as live:
            self._live = live
            
            def add_line(line: str):
                """Add a line to the output buffer."""
                # Clean up the line - remove ANSI codes and extra whitespace
                import re
                line = re.sub(r'\x1b\[[0-9;]*m', '', line)  # Remove color codes
                line = re.sub(r'\x1b\[[0-9]*[A-Z]', '', line)  # Remove cursor movement
                line = line.replace('\r', '').strip()
                
                if line:
                    self._output_buffer.append(line)
                    # Keep total buffer reasonable
                    if len(self._output_buffer) > 50:
                        self._output_buffer = self._output_buffer[-30:]
                    # Update display immediately
                    self._live.update(generate_display())
                        
            yield add_line
            
        self._live = None
        
    def phase_header(self, phase: str, current: int = None, total: int = None):
        """Display a phase header with optional progress."""
        if current and total:
            text = f"[bold cyan]Phase {current}/{total}:[/bold cyan] {phase}"
        else:
            text = f"[bold cyan]{phase}[/bold cyan]"
        self.console.print(text)
        
    def create_confirmation_prompt(self, config: Dict[str, Any]) -> bool:
        """Create a nice confirmation prompt."""
        self.container_config(config)
        return self.console.input("\n[bold]Proceed with container creation?[/bold] [green]([Y]/n)[/green]: ").lower() != 'n'


# Global instance
output = OutputManager()