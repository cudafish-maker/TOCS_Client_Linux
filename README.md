# TOCS Client — Tactical Operations Command Software

A PyQt6 desktop application for field operators. Connects to a TOCS Server over a mesh network (Yggdrasil, I2P, or LoRa/RNode) to synchronize assets, SITREPs, and real-time chat — no internet required.

---

## Features

- **Interactive map** — Leaflet.js map with markers for all operators, safe houses, caches, and transmitter sites. Per-type visibility toggles in the asset panel.
- **Asset management** — Submit and update your operator profile, track field assets by type and status with GPS coordinates.
- **SITREPs** — File situation reports with severity levels; reports sync to the server and all connected operators.
- **Integrated mesh chat** — Group broadcast and private messaging over Reticulum/LXMF. Peer discovery is automatic — no configuration needed.
- **RNode Config** — View your radio settings alongside the server's. One-click sync to match the server's frequency, bandwidth, spreading factor, and coding rate.
- **Offline login** — Cached credentials allow login when the server is temporarily unreachable.
- **Custom asset types** — The server can define additional asset types (e.g. "Food Bank", "Medical Post") which automatically appear on all clients.

---

## Network Transports

TOCS uses the [Reticulum Network Stack](https://reticulum.network) and works over any combination of:

| Transport | Use case |
|-----------|----------|
| **Yggdrasil** | Primary — encrypted IPv6 mesh over the internet or LAN |
| **I2P** | Anonymous overlay network |
| **RNode (LoRa)** | Off-grid radio — no internet, long range |
| **AutoInterface** | Automatic LAN discovery |

---

## Requirements

- Python 3.10+
- Linux (Debian/Ubuntu recommended)
- `sudo` access (for Yggdrasil install)

Python packages (installed automatically by `setup.sh`):

```
rns >= 0.7.0
lxmf >= 0.4.0
PyQt6 >= 6.6.0
PyQt6-WebEngine >= 6.6.0
```

---

## Installation

```bash
git clone https://github.com/cudafish-maker/TOCS_Client_Linux.git
cd TOCS_Client_Linux
bash setup.sh
```

`setup.sh` will:

1. Check Python 3.10+ and install pip / venv if needed
2. Create a virtual environment (`venv/`) and install Python dependencies
3. Download and install **Yggdrasil** (auto-detects amd64 / arm64 / armhf)
4. Inject public peers into the Yggdrasil config and start the service
5. Optionally configure **I2P** (if `i2prouter` or `i2pd` is installed)
6. Optionally configure an **RNode** LoRa radio (detects serial port, uses 915 MHz defaults)
7. Write a Reticulum config pre-pointed at the TOCS server
8. Create a `tocs_client.sh` launch script

---

## First Launch

```bash
bash tocs_client.sh
```

A login dialog will appear. On first use, go to the **Register** tab and enter:

- Your callsign
- A password
- The **registration passphrase** — ask your network administrator for this

After registration your operator profile is created on the server and you will be placed on the shared map.

---

## Usage

### Toolbar

| Button | Action |
|--------|--------|
| **+ Asset** | Submit a new field asset |
| **+ SITREP** | File a situation report |
| **RNode Config** | View and sync LoRa radio settings |
| **Chat** | Toggle the chat panel |

### Asset Panel (left)

Lists all assets grouped by type. Each type group has a **checkbox** — uncheck to hide that type on the map.

Click any asset to view its details. Click your own operator entry to edit your profile and position.

### Map

- Click an asset marker to open its detail/edit dialog
- Use **+ Asset** or **+ SITREP**, then click **Pick on Map** to place it at a specific location
- Press **Esc** to cancel placement mode

### Chat Panel (bottom dock)

- Type a message and press **Enter** or click **Send** to broadcast to all online operators
- Use `/msg <callsign> <message>` to send a private message
- Double-click a peer in the list to start a private conversation
- Peers are discovered automatically — no addresses to configure

### RNode Config

Open from the toolbar to see your current LoRa radio parameters alongside the server's recommended settings. Click **Sync to Server** to apply the server's frequency, bandwidth, spreading factor, and coding rate to your local Reticulum config. Your device port is never overwritten.

> A restart is required for radio setting changes to take effect.

---

## Command-line Options

```
python3 main.py [--rns-config <dir>] [--loglevel <0-7>]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--rns-config` | `~/.config/reticulum` | Reticulum config directory |
| `--loglevel` | `2` | RNS log verbosity (0=critical, 7=extreme) |

---

## Asset Types

Built-in types:

| Type | Description |
|------|-------------|
| **Operator** | A registered field operator |
| **Safe House** | Secure location with codename and capacity |
| **Cache** | Supply cache with contents description |
| **Transmitter Site** | Radio site with frequency and TX type |

Custom types can be added by the server administrator and will automatically sync to all clients.

---

## File Layout

```
tocs_client/
  main.py                  # Entry point
  setup.sh                 # Installer
  requirements.txt
  models/                  # Asset and SITREP dataclasses
  db/                      # SQLite repository layer
  controllers/             # Business logic
  sync/                    # Reticulum sync client + protocol
    rns_sync.py            # SyncClient — discovers server, auth, data sync
    protocol.py            # Message type constants + serialization
    rnode_config.py        # Read/write RNode settings in Reticulum config
  chat/                    # LXMF mesh chat (node, peers, messaging)
  map/                     # Leaflet map (QWebEngineView + QWebChannel bridge)
  ui/                      # PyQt6 windows and dialogs
```

---

## License

MIT
