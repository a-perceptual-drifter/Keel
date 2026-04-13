# Running Keel as a systemd service (Linux)

Persist the scheduler across reboots. Unit file below installs as a user service
so Keel runs under your own UID and writes to your own `$HOME/keel/store/`.

```ini
# ~/.config/systemd/user/keel.service
[Unit]
Description=Keel personal feed agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=%h/keel
ExecStart=%h/keel/.venv/bin/keel --schedule
Restart=on-failure
RestartSec=15
StandardOutput=journal
StandardError=journal
SyslogIdentifier=keel
# If using the vault with a master password, set via EnvironmentFile.
# Environment=KEEL_VAULT_KEY=...

[Install]
WantedBy=default.target
```

Enable and start:

```bash
systemctl --user daemon-reload
systemctl --user enable --now keel.service
journalctl --user -u keel -f
```

Journald rotation is configured in `/etc/systemd/journald.conf`
(`SystemMaxUse=500M` is a reasonable ceiling).
