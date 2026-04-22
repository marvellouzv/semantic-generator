# -*- coding: utf-8 -*-
"""
Force UTF-8 encoding for console output on Windows
This file is loaded automatically by Python interpreter
"""
import sys
import io

# Force UTF-8 encoding for stdout and stderr on Windows
if sys.platform.startswith('win'):
    # Reconfigure stdout and stderr to use UTF-8
    if sys.stdout:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    if sys.stderr:
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
