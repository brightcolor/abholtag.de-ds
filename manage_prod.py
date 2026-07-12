#!/usr/bin/env python
"""Entry point for the root-layout application (Docker/production).

The repository's manage.py currently targets an alternative src/ layout;
this file always runs the root config/apps packages.
"""
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
