#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `celery_worker_serverless` package."""

import pytest

from click.testing import CliRunner

import celery_serverless
from celery_serverless import cli


def test_command_line_interface():
    """Test the CLI."""
    runner = CliRunner()
    result = runner.invoke(cli.main)
    # assert result.exit_code == 0
    # assert 'celery_serverless.cli.main' in result.output
    # help_result = runner.invoke(cli.main, ['--help'])
    # assert help_result.exit_code == 0
    # assert '--help  Show this message and exit.' in help_result.output


def test_handler_minimal_call():
    from celery_serverless import handler_worker
    response = handler_worker(None, None)
    assert response
