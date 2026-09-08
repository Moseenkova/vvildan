#!/usr/bin/env python3
"""Run with sudo to route labhealth.pro's homepage to the existing frontend."""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


def main():
    config = Path('/etc/nginx/sites-enabled/labhealth.pro').resolve(strict=True)
    snippet = Path(__file__).resolve().parents[1] / 'deploy/nginx/labhealth-locations.conf'
    original = config.read_text()
    if re.search(r'location\s+/\s*\{', original):
        raise SystemExit('A homepage location already exists; review it before changing it.')
    marker = '    location = /webapp {'
    if original.count(marker) != 1:
        raise SystemExit('Expected webapp configuration not found; no changes made.')
    block = '\n'.join('    ' + line if line else '' for line in snippet.read_text().splitlines())
    updated = original.replace(marker, block + '\n\n' + marker, 1)

    if os.geteuid() != 0:
        raise SystemExit('Run this script with sudo to update and reload Nginx.')

    with tempfile.NamedTemporaryFile(prefix='labhealth.pro.backup.', dir=config.parent, delete=False) as backup:
        backup_path = Path(backup.name)
    shutil.copy2(config, backup_path)
    try:
        config.write_text(updated)
        subprocess.run(['nginx', '-t', '-c', '/etc/nginx/nginx.conf'], check=True)
        # The host Nginx runs independently of the masked systemd service.
        subprocess.run(['nginx', '-c', '/etc/nginx/nginx.conf', '-s', 'reload'], check=True)
    except Exception:
        shutil.copy2(backup_path, config)
        subprocess.run(['nginx', '-c', '/etc/nginx/nginx.conf', '-s', 'reload'], check=False)
        raise
    print(f'Homepage route installed. Original configuration saved at {backup_path}')


if __name__ == '__main__':
    main()
