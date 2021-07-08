#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Utility CLI to aid in AiiDAlab development."""
# pylint: disable=invalid-name,too-many-branches
import logging
import json
from pathlib import Path
from subprocess import run

import click
import dulwich
import toml
from tabulate import tabulate

import aiidalab.config
from aiidalab.app import AiidaLabApp
from aiidalab.utils import load_app_registry_entry
from aiidalab.utils import load_app_registry_index


logging.basicConfig(level=logging.DEBUG)


_FMT_BOOL_AND_NONE = {None: "n/a", False: "no", True: "yes"}



def _get_app_from_name(name):
    """Return the app instance from name."""
    apps = load_app_registry()['apps']
    app_data = apps.get(name)
    if app_data is None:
        click.secho(f"Did not find app '{name}' in app registry.", fg='yellow')
    return AiidaLabApp(name, app_data, aiidalab.config.AIIDALAB_APPS, watch=False)


def _get_app():
    """Return the app instance from the current working directory."""
    try:
        name = str(Path.cwd().relative_to(aiidalab.config.AIIDALAB_APPS))
        if name == '.':
            raise ValueError
    except ValueError:
        raise click.ClickException(f"The current directory is not a sub-directory of '{aiidalab.config.AIIDALAB_APPS}'.")

    try:
        return _get_app_from_name(name)
    except dulwich.errors.NotGitRepository:
        raise click.ClickException("The app directory must be a git repository.")


@click.group()
@click.option('--local-prefix', type=click.Path(), default='~/local')
@click.pass_context
def cli(ctx, local_prefix):
    """Manage the AiiDAlab development environment."""
    ctx.ensure_object(dict)

    apps_path = Path(aiidalab.config.AIIDALAB_APPS).resolve()
    local_prefix = Path(local_prefix).expanduser()

    class Paths:  # noqa
        """Internal class to pass computed paths sub-commands."""

        home_app_system = Path('/opt/aiidalab-home')
        home_app_user = apps_path.joinpath('home')

        aiidalab_dev = local_prefix.joinpath('aiidalab')
        aiidalab_dev_package = aiidalab_dev.joinpath('aiidalab')

        aiidalab_home_dev = local_prefix.joinpath('aiidalab-home')
        aiidalab_home_dev_aiidalab_link = aiidalab_home_dev.joinpath('aiidalab')

        home_app_system = Path('/opt/aiidalab-home')
        home_app_user = apps_path.joinpath('home')

        config_file = Path.home() / 'aiidalab.toml'

    ctx.obj['paths'] = Paths


@cli.command()
def config():
    """Show the current configuration."""
    cfg = {key[len('AIIDALAB_'):].lower() : getattr(aiidalab.config, key)
           for key in dir(aiidalab.config) if key.startswith('AIIDALAB_')}
    click.echo(toml.dumps(cfg))


@cli.command()
@click.option('-a', '--app')
def registry(app):
    """Show the registry."""
    if app:
        click.echo(json.dumps(load_app_registry_entry(app), indent=2))
    else:
        click.echo(json.dumps(load_app_registry_index(), indent=2))


@cli.command()
@click.pass_context
def restore(ctx):
    """Restore the system configuration of the home app."""
    paths = ctx.obj['paths']

    assert paths.home_app_system.exists()

    if paths.home_app_user.exists():
        if paths.home_app_user.is_symlink():
            if paths.home_app_user.resolve() == paths.aiidalab_home_dev.resolve():
                click.echo(f"Link {paths.home_app_user} -> {paths.home_app_system}")
                paths.home_app_user.unlink()
                paths.home_app_user.symlink_to(paths.home_app_system)
            elif paths.home_app_user.resolve() != paths.home_app_system.resolve():
                raise click.ClickException(f"Link {paths.home_app_user} exists and points to unexpected location.")
        else:
            raise click.ClickException(f"{paths.home_app_user} exists and is not expected symbolic link.")
    else:
        click.echo(f"Link {paths.home_app_user} -> {paths.home_app_system}")
        paths.home_app_user.symlink_to(paths.home_app_system)

    try:
        config = toml.loads(paths.config_file.read_text())
        config['develop'] = False
        paths.config_file.write_text(toml.dumps(config))
    except FileNotFoundError:
        pass  # config file does not exist, nothing to do

    click.secho("Mode: SYSTEM", fg='green')


@cli.command()
@click.pass_context
def status(ctx):
    """Show current status of the AiiDAlab environment."""
    paths = ctx.obj['paths']

    issues = False

    def msg_issue(msg):
        nonlocal issues
        issues = True
        click.secho(f"\u2718 {msg}", fg='red')

    def msg_ok(msg):
        click.secho(f"\u2714 {msg}", fg='green')

    dev_mode = paths.home_app_user.resolve() == paths.aiidalab_home_dev.resolve()
    system_mode = paths.home_app_user.resolve() == paths.home_app_system.resolve()

    mode = 'DEVELOPMENT' if dev_mode else ('SYSTEM' if system_mode else 'UNKNOWN')
    click.secho(f"Mode: {mode}")

    if dev_mode:
        if paths.aiidalab_dev.is_dir():
            msg_ok(f"Directory {paths.aiidalab_dev} exists.")
        else:
            msg_issue(f"Directory {paths.aiidalab_dev} does not exist.")

        if paths.aiidalab_home_dev.is_dir():
            msg_ok(f"Directory {paths.aiidalab_home_dev} exists.")
        else:
            msg_issue(f"Directory {paths.aiidalab_home_dev} does not exist.")

        try:
            config = toml.loads(paths.config_file.read_text())
        except FileNotFoundError:
            msg_issue(f"File '{paths.config_file!s}' does not exist.")
        else:
            if config.get('develop'):
                msg_ok(f"Key 'develop' set to True in '{paths.config_file!s}'.")
            else:
                msg_issue(f"Key 'develop' not set to True in '{paths.config_file!s}'.")

        if paths.aiidalab_home_dev_aiidalab_link.resolve() == paths.aiidalab_dev_package.resolve():
            msg_ok(f"Link {paths.aiidalab_home_dev_aiidalab_link} to {paths.aiidalab_dev_package} is set.")
        else:
            msg_issue(f"Link {paths.aiidalab_home_dev_aiidalab_link} to {paths.aiidalab_dev_package} is missing.")

        if paths.home_app_user.resolve() == paths.aiidalab_home_dev.resolve():
            msg_ok(f"Link {paths.home_app_user} to {paths.aiidalab_home_dev} is set.")
        else:
            msg_issue(f"Link {paths.home_app_user} to {paths.aiidalab_home_dev} is missing.")
    elif system_mode:
        msg_ok(f"Link {paths.home_app_user} to {paths.home_app_system} is set.")

        try:
            config = toml.loads(paths.config_file.read_text())
        except FileNotFoundError:
            msg_ok(f"Local config file '{paths.config_file!s}' does not exist.")
        else:
            if config.get('develop'):
                msg_issue(f"Key 'develop' set to True in '{paths.config_file!s}'.")
            else:
                msg_ok(f"Key 'develop' not set to True in '{paths.config_file!s}'.")

    elif paths.home_app_user.exists():
        msg_issue("The home app is installed, but is either a local directory or points to an unknown location.")

    else:
        msg_issue("The home app is not installed.")

    if issues:
        raise click.ClickException("Detected one or more issues.")


@cli.command()
@click.pass_context
@click.option('-u', '--github-username', default='aiidalab')
@click.option('--use-ssh', is_flag=True)
def setup(ctx, github_username, use_ssh):
    """Set up the AiiDAlab environment for development."""
    paths = ctx.obj['paths']

    aiidalab_url = f"git@github.com:{github_username}/aiidalab.git" if use_ssh else \
            f"https://github.com/{github_username}/aiidalab.git"
    aiidalab_home_url = f"git@github.com:{github_username}/aiidalab-home.git" if use_ssh else \
            f"https://github.com/{github_username}/aiidalab-home.git"

    # Setup aiidalab package development directory.
    if not paths.aiidalab_dev.exists():
        run(['git', 'clone', aiidalab_url, paths.aiidalab_dev], check=True)

    # Setup aiidalab-home development directory.
    if not paths.aiidalab_home_dev.exists():
        run(['git', 'clone', aiidalab_home_url, paths.aiidalab_home_dev], check=True)

    # Link aiidalab development package into aiidalab-home development directory.
    if paths.aiidalab_home_dev_aiidalab_link.exists():
        if paths.aiidalab_home_dev_aiidalab_link.resolve() != paths.aiidalab_dev_package.resolve():
            raise click.ClickException(
                f"Link {paths.aiidalab_home_dev_aiidalab_link} already exists and points to unknown location.")
    else:
        click.echo(f"Link {paths.aiidalab_home_dev_aiidalab_link} -> {paths.aiidalab_dev_package}")
        paths.aiidalab_home_dev_aiidalab_link.symlink_to(paths.aiidalab_dev_package, target_is_directory=True)

    # Link aiidalab-home development development directory into apps directory.
    if paths.home_app_user.exists():
        if paths.home_app_user.is_symlink():
            if paths.home_app_user.resolve() == paths.home_app_system.resolve():
                click.echo(f'Unlink {paths.home_app_user}')
                paths.home_app_user.unlink()
                click.echo(f"Link {paths.home_app_user} -> {paths.aiidalab_home_dev}")
                paths.home_app_user.symlink_to(paths.aiidalab_home_dev, target_is_directory=True)
            elif paths.home_app_user.resolve() != paths.aiidalab_home_dev.resolve():
                raise click.ClickException(f"Link {paths.home_app_user} already exists and points at unknown location.")
        elif paths.home_app_user.is_dir():
            raise click.ClickException(
                f"Unable to setup home app for development, exxisting directory at {paths.home_app_user}.")
    else:
        click.echo(f"Link {paths.home_app_user} -> {paths.aiidalab_home_dev}")
        paths.home_app_user.symlink_to(paths.aiidalab_home_dev, target_is_directory=True)

    # Set 'develop' key in local aiidalab config.
    try:
        config = toml.loads(paths.config_file.read_text())
    except FileNotFoundError:
        config = dict()
    config['develop'] = True
    paths.config_file.write_text(toml.dumps(config))

    click.secho("Mode: DEVELOPMENT", fg='green')


@cli.command()
def app():
    """Show basic information about an app and the installation status."""
    app = _get_app()
    rows = list()
    rows.append(("AiiDAlab app", app.name))
    rows.append(("Version:", app.installed_version))
    rows.append(("Detached:", _FMT_BOOL_AND_NONE[app.detached]))
    rows.append(("Compatible:", _FMT_BOOL_AND_NONE[app.compatible]))

    click.echo(tabulate(rows))



if __name__ == '__main__':
    cli(auto_envvar_prefix='AIIDALAB_DEVELOP')  # noqa
