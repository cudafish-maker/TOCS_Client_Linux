#!/bin/bash
# =============================================================================
# TOCS Client Setup Script
# =============================================================================
# Installs Python dependencies, configures Yggdrasil (automatic), and
# optionally configures I2P for Reticulum.
#
# Run with:  bash setup.sh
# =============================================================================

set -e

# ── Pre-filled server configuration ──────────────────────────────────────────
SERVER_YGGDRASIL_IP="202:3bad:f9d4:ca51:2d43:b179:8a16:8d2a"
SERVER_RNS_PORT="4242"

# Public Yggdrasil peers — used to reach the Yggdrasil network
PUBLIC_PEERS=(
    "tcp://yggno.de:11129"
    "tcp://ygg.litedev.org:11129"
    "tls://ygg.mkg20001.io:443"
    "tcp://[2a01:4f9:c010:664f::1]:11129"
)
# =============================================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[OK]${NC}  $*"; }
warn() { echo -e "${YELLOW}[!!]${NC}  $*"; }
err()  { echo -e "${RED}[ERR]${NC} $*"; exit 1; }
info() { echo -e "${CYAN}[--]${NC}  $*"; }
hdr()  { echo -e "\n${BOLD}=== $* ===${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RNS_CONFIG_DIR="$HOME/.config/reticulum"

# ─────────────────────────────────────────────────────────────────────────────
hdr "TOCS Client Setup"
# ─────────────────────────────────────────────────────────────────────────────

# ── Python check ─────────────────────────────────────────────────────────────
hdr "Checking Python"
if ! command -v python3 &>/dev/null; then
    err "python3 not found. Install with: sudo apt install python3"
fi
PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    err "Python 3.10+ required (found $PY_VER). Please upgrade Python first."
fi
ok "Python $PY_VER"

info "Installing python3-pip and python3-venv..."
sudo apt install -y python3-pip python3-venv

# ── Virtual environment ───────────────────────────────────────────────────────
hdr "Setting Up Virtual Environment"
VENV_DIR="$SCRIPT_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    ok "Virtual environment created: $VENV_DIR"
else
    ok "Virtual environment already exists: $VENV_DIR"
fi

# Bootstrap pip inside the venv in case ensurepip was unavailable
if ! "$VENV_DIR/bin/python" -m pip --version &>/dev/null; then
    info "Bootstrapping pip in venv..."
    sudo apt install -y python3-pip
    "$VENV_DIR/bin/python" -m ensurepip --upgrade 2>/dev/null \
        || curl -sS https://bootstrap.pypa.io/get-pip.py | "$VENV_DIR/bin/python"
fi

# ── Python dependencies ───────────────────────────────────────────────────────
hdr "Installing Python Dependencies"
"$VENV_DIR/bin/python" -m pip install --upgrade pip -q
"$VENV_DIR/bin/python" -m pip install -r "$SCRIPT_DIR/requirements.txt"
ok "Python dependencies installed"

# ─────────────────────────────────────────────────────────────────────────────
hdr "Installing Yggdrasil"
# ─────────────────────────────────────────────────────────────────────────────

install_yggdrasil() {
    ARCH=$(dpkg --print-architecture 2>/dev/null || uname -m)
    YGG_VER="0.5.13"

    case "$ARCH" in
        amd64|x86_64)  DL_ARCH="amd64" ;;
        arm64|aarch64) DL_ARCH="arm64" ;;
        armhf|armv7l)  DL_ARCH="armhf" ;;
        *)
            err "Unsupported architecture: $ARCH. Install Yggdrasil manually from https://github.com/yggdrasil-network/yggdrasil-go/releases"
            ;;
    esac

    PKG="yggdrasil-${YGG_VER}-${DL_ARCH}.deb"
    DL_URL="https://github.com/yggdrasil-network/yggdrasil-go/releases/download/v${YGG_VER}/${PKG}"
    TMP_DEB="/tmp/${PKG}"

    info "Downloading Yggdrasil $YGG_VER for $DL_ARCH..."
    if command -v curl &>/dev/null; then
        curl -L -o "$TMP_DEB" "$DL_URL"
    elif command -v wget &>/dev/null; then
        wget -O "$TMP_DEB" "$DL_URL"
    else
        err "curl or wget is required to download Yggdrasil."
    fi
    sudo dpkg -i "$TMP_DEB"
    rm -f "$TMP_DEB"
}

if command -v yggdrasil &>/dev/null; then
    INSTALLED_VER=$(yggdrasil --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1)
    ok "Yggdrasil already installed ($INSTALLED_VER)"
else
    install_yggdrasil
    ok "Yggdrasil installed"
fi

# ── Configure Yggdrasil ───────────────────────────────────────────────────────
hdr "Configuring Yggdrasil"

YGG_CONF="/etc/yggdrasil/yggdrasil.conf"

if [ ! -f "$YGG_CONF" ]; then
    info "Generating Yggdrasil config..."
    sudo mkdir -p /etc/yggdrasil
    sudo yggdrasil -genconf | sudo tee "$YGG_CONF" > /dev/null
fi

info "Injecting peers into Yggdrasil config..."
PEERS_JSON=$(printf '"%s", ' "${PUBLIC_PEERS[@]}")
PEERS_JSON="[${PEERS_JSON%, }]"

sudo python3 - "$YGG_CONF" "$PEERS_JSON" << 'PYEOF'
import sys, re

conf_path = sys.argv[1]
peers_json = sys.argv[2]

with open(conf_path, 'r') as f:
    content = f.read()

new_block = f'  Peers: {peers_json}'
content = re.sub(r'\s*Peers:\s*\[.*?\]', '\n' + new_block, content, flags=re.DOTALL)

with open(conf_path, 'w') as f:
    f.write(content)

print("  Peers updated.")
PYEOF

info "Enabling and starting Yggdrasil..."
sudo systemctl enable yggdrasil
sudo systemctl restart yggdrasil

# Wait for Yggdrasil IPv6 address
info "Waiting for Yggdrasil address..."
YGG_IP=""
for i in $(seq 1 20); do
    YGG_IP=$(ip addr show 2>/dev/null | grep -oP '(?<=inet6 )2[0-9a-f:]+(?=/7)' | head -1)
    [ -n "$YGG_IP" ] && break
    sleep 1
done

if [ -n "$YGG_IP" ]; then
    ok "Yggdrasil up — this node's address: $YGG_IP"
else
    warn "Yggdrasil started but address not yet visible. This can be normal on first launch."
    YGG_IP="(pending — check with: ip addr show | grep '/7')"
fi

# ─────────────────────────────────────────────────────────────────────────────
hdr "RNode Configuration"
# ─────────────────────────────────────────────────────────────────────────────

USE_RNODE=false
RNODE_PORT=""

read -rp "  Do you have an RNode LoRa radio? [y/N]: " yn
if [[ "$yn" =~ ^[Yy] ]]; then
    # Try to auto-detect a likely serial port
    DETECTED_PORT=""
    for p in /dev/ttyUSB0 /dev/ttyUSB1 /dev/ttyACM0 /dev/ttyACM1; do
        [ -e "$p" ] && { DETECTED_PORT="$p"; break; }
    done

    if [ -n "$DETECTED_PORT" ]; then
        info "Detected serial device: $DETECTED_PORT"
        read -rp "  RNode port [$DETECTED_PORT]: " user_port
        RNODE_PORT="${user_port:-$DETECTED_PORT}"
    else
        read -rp "  RNode port (e.g. /dev/ttyUSB0): " user_port
        RNODE_PORT="$user_port"
    fi

    if [ -n "$RNODE_PORT" ]; then
        USE_RNODE=true
        ok "RNode will be configured on $RNODE_PORT"
        info "Default radio parameters: 915 MHz, BW 125 kHz, SF11, CR 4/8, 17 dBm"
        info "Use 'RNode Config' in the TOCS menu to sync settings from the server."
    else
        warn "No port entered — skipping RNode configuration."
    fi
else
    info "Skipping RNode configuration."
fi

# ─────────────────────────────────────────────────────────────────────────────
hdr "I2P Configuration"
# ─────────────────────────────────────────────────────────────────────────────

USE_I2P=false

if command -v i2prouter &>/dev/null || command -v i2pd &>/dev/null; then
    if ss -tlnp 2>/dev/null | grep -q 7656; then
        ok "I2P SAM bridge detected on port 7656"
        read -rp "  Enable I2P interface for TOCS? [Y/n]: " yn
        [[ ! "$yn" =~ ^[Nn] ]] && USE_I2P=true
    else
        warn "I2P router found but SAM bridge is not active on port 7656."
        echo "  Java I2P: enable SAM at http://127.0.0.1:7657/configclients"
        echo "  i2pd:     add 'enabled = true' under [sam] in /etc/i2pd/i2pd.conf, then restart i2pd"
        read -rp "  Enable I2P anyway (requires SAM before running TOCS)? [y/N]: " yn
        [[ "$yn" =~ ^[Yy] ]] && USE_I2P=true
    fi
else
    info "No I2P router found — skipping I2P interface."
    echo "  Install options:"
    echo "    Java I2P:  https://geti2p.net"
    echo "    i2pd:      sudo apt install i2pd"
    echo "  Re-run setup.sh after installing I2P to enable this interface."
fi

# ─────────────────────────────────────────────────────────────────────────────
hdr "Configuring Reticulum"
# ─────────────────────────────────────────────────────────────────────────────

mkdir -p "$RNS_CONFIG_DIR"
RNS_CONF="$RNS_CONFIG_DIR/config"

# Build interface blocks
I2P_BLOCK=""
if [ "$USE_I2P" = true ]; then
    I2P_BLOCK="
  [[I2P Interface]]
    type = I2PInterface
    enabled = yes
    peer_name = tocs_i2p
    connectable = yes
"
fi

RNODE_BLOCK=""
if [ "$USE_RNODE" = true ]; then
    RNODE_BLOCK="
  # RNode LoRa — 915 MHz, medium-to-long range defaults
  # Use 'RNode Config' in TOCS to sync settings from the server
  [[RNode LoRa 915MHz]]
    type = RNodeInterface
    enabled = yes
    port = $RNODE_PORT
    frequency = 915000000
    bandwidth = 125000
    txpower = 17
    spreadingfactor = 11
    codingrate = 8
"
fi

cat > "$RNS_CONF" << RNSEOF
# Reticulum config — generated by TOCS Client setup.sh

[reticulum]
  enable_transport = False
  share_instance = Yes
  instance_name = default

[logging]
  loglevel = 2

[interfaces]

  # Local discovery — finds other TOCS nodes on your LAN automatically
  [[Local]]
    type = AutoInterface
    enabled = yes

  # TOCS Server via Yggdrasil mesh network
  [[TOCS Server (Yggdrasil)]]
    type = TCPClientInterface
    enabled = yes
    target_host = $SERVER_YGGDRASIL_IP
    target_port = $SERVER_RNS_PORT
${I2P_BLOCK}${RNODE_BLOCK}
RNSEOF

ok "Reticulum config written to $RNS_CONF"

# ─────────────────────────────────────────────────────────────────────────────
hdr "Creating Launch Script"
# ─────────────────────────────────────────────────────────────────────────────

LAUNCHER="$SCRIPT_DIR/tocs_client.sh"
cat > "$LAUNCHER" << LAUNCHEOF
#!/bin/bash
cd "\$(dirname "\$0")"
venv/bin/python main.py --rns-config "$RNS_CONFIG_DIR" "\$@"
LAUNCHEOF
chmod +x "$LAUNCHER"
ok "Launcher: $LAUNCHER"

# ─────────────────────────────────────────────────────────────────────────────
hdr "Setup Complete"
# ─────────────────────────────────────────────────────────────────────────────

echo ""
echo -e "  ${GREEN}Your Yggdrasil address:${NC}  $YGG_IP"
echo -e "  ${GREEN}TOCS server address:${NC}     $SERVER_YGGDRASIL_IP"
echo -e "  ${GREEN}Reticulum config:${NC}        $RNS_CONF"
echo ""
echo "  Interfaces configured:"
echo -e "    ${GREEN}✓${NC} Yggdrasil → TOCS Server ($SERVER_YGGDRASIL_IP:$SERVER_RNS_PORT)"
[ "$USE_I2P"   = true ] && echo -e "    ${GREEN}✓${NC} I2P"
[ "$USE_RNODE" = true ] && echo -e "    ${GREEN}✓${NC} RNode LoRa ($RNODE_PORT, 915 MHz)"
echo ""
echo "  To start TOCS Client:"
echo -e "    ${CYAN}bash tocs_client.sh${NC}"
echo ""
echo "  On first launch you will be prompted to register."
echo "  Ask your server administrator for the registration passphrase."
echo ""
