#!/usr/bin/env python3
"""Main CLI entry point for pxrun."""

import sys
import logging
import warnings
import os
import click

# Suppress all warnings unless in debug mode
if '--debug' not in sys.argv:
    warnings.filterwarnings('ignore')
    os.environ['PYTHONWARNINGS'] = 'ignore'
    # Suppress urllib3 warnings specifically
    import urllib3
    urllib3.disable_warnings()

from src.cli import __version__
from src.cli.commands.create import create
from src.cli.commands.destroy import destroy
from src.cli.commands.list import list_containers
from src.cli.commands.save_config import save_config
from src.cli.commands.setup import setup
from src.cli.commands.tailscale import tailscale


@click.group()
@click.version_option(version=__version__, prog_name='pxrun')
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.pass_context
def cli(ctx, debug):
    """pxrun - Proxmox LXC container management tool.

    Manage LXC containers on Proxmox VE clusters with ease.
    """
    # Setup logging - suppress INFO unless debug
    if debug:
        level = logging.DEBUG
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    else:
        level = logging.WARNING  # Only show warnings and errors
        log_format = '%(message)s'
    
    logging.basicConfig(
        level=level,
        format=log_format
    )

    # Store debug flag in context
    ctx.ensure_object(dict)
    ctx.obj['DEBUG'] = debug

    # Load credentials on startup
    from src.services.credentials import CredentialsManager
    creds = CredentialsManager()
    creds.load_env_file()


# Register commands
cli.add_command(create)
cli.add_command(destroy)
cli.add_command(list_containers)
cli.add_command(save_config)
cli.add_command(setup)
cli.add_command(tailscale)


def main():
    """Main entry point."""
    try:
        cli()
    except Exception as e:
        if '--debug' in sys.argv:
            raise
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()