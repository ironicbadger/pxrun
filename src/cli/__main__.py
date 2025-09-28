#!/usr/bin/env python3
"""Main CLI entry point for pxrun."""

import sys
import logging
import click

from src.cli import __version__
from src.cli.commands.create import create
from src.cli.commands.destroy import destroy
from src.cli.commands.list import list_containers
from src.cli.commands.save_config import save_config
from src.cli.commands.setup import setup


@click.group()
@click.version_option(version=__version__, prog_name='pxrun')
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.pass_context
def cli(ctx, debug):
    """pxrun - Proxmox LXC container management tool.

    Manage LXC containers on Proxmox VE clusters with ease.
    """
    # Setup logging
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(levelname)s: %(message)s' if not debug else '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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