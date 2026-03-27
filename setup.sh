#!/bin/bash
# =============================================================================
# TOCS Client Setup Script
# =============================================================================
# Run with:  bash setup.sh
# Must be run from inside the tocs_client directory.
# =============================================================================

set -e

# ── Server configuration (pre-filled) ────────────────────────────────────────
SERVER_YGGDRASIL_IP="202:3bad:f9d4:ca51:2d43:b179:8a16:8d2a"
SERVER_RNS_PORT="4242"

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
err()  { echo -e "${RED}[ERR]${NC} $*" >&2; exit 1; }
info() { echo -e "${CYAN}[--]${NC}  $*"; }
hdr()  { echo -e "\n${BOLD}=== $* ===${NC}"; }

# ── Working directory ─────────────────────────────────────────────────────────
# Always run from the directory containing this script
cd "$(dirname "$0")"
SCRIPT_DIR="$(pwd)"
RNS_CONFIG_DIR="$HOME/.config/reticulum"

hdr "TOCS Client Setup"
info "Working directory: $SCRIPT_DIR"

[ -f "$SCRIPT_DIR/requirements.txt" ] || err "requirements.txt not found. Run setup.sh from inside the tocs_client directory."

# ── Python ────────────────────────────────────────────────────────────────────
hdr "Checking Python"
command -v python3 &>/dev/null || err "python3 not found — install with: sudo apt install python3"

PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    err "Python 3.10+ required (found $PY_VER)"
fi
ok "Python $PY_VER"

# ── System packages ───────────────────────────────────────────────────────────
hdr "Installing System Packages"
sudo apt-get update -qq
sudo apt-get install -y python3-venv python3-pip curl wget
ok "System packages ready"

# ── Virtual environment ───────────────────────────────────────────────────────
hdr "Setting Up Virtual Environment"
VENV="$SCRIPT_DIR/venv"

if [ -d "$VENV" ]; then
    info "Removing existing virtual environment..."
    rm -rf "$VENV"
fi

python3 -m venv "$VENV"
ok "Virtual environment created"

# Ensure pip is available inside the venv
if ! "$VENV/bin/python" -m pip --version &>/dev/null 2>&1; then
    info "pip not found in venv — bootstrapping..."
    curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
    "$VENV/bin/python" /tmp/get-pip.py
    rm -f /tmp/get-pip.py
fi

ok "pip available: $("$VENV/bin/python" -m pip --version)"

# ── Python dependencies ───────────────────────────────────────────────────────
hdr "Installing Python Dependencies"
"$VENV/bin/python" -m pip install --upgrade pip -q
"$VENV/bin/python" -m pip install -r "$SCRIPT_DIR/requirements.txt"
ok "Python dependencies installed"

# ── Yggdrasil ─────────────────────────────────────────────────────────────────
hdr "Installing Yggdrasil"

install_yggdrasil() {
    ARCH=$(dpkg --print-architecture 2>/dev/null || uname -m)
    YGG_VER="0.5.13"
    case "$ARCH" in
        amd64|x86_64)  DL_ARCH="amd64" ;;
        arm64|aarch64) DL_ARCH="arm64" ;;
        armhf|armv7l)  DL_ARCH="armhf" ;;
        *) err "Unsupported architecture: $ARCH" ;;
    esac
    PKG="yggdrasil-${YGG_VER}-${DL_ARCH}.deb"
    URL="https://github.com/yggdrasil-network/yggdrasil-go/releases/download/v${YGG_VER}/${PKG}"
    TMP="/tmp/${PKG}"
    info "Downloading Yggdrasil $YGG_VER ($DL_ARCH)..."
    curl -L -o "$TMP" "$URL"
    sudo dpkg -i "$TMP"
    rm -f "$TMP"
}

if command -v yggdrasil &>/dev/null; then
    VER=$(yggdrasil --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1)
    ok "Yggdrasil already installed ($VER)"
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

info "Injecting peers..."
PEERS_JSON=$(printf '"%s", ' "${PUBLIC_PEERS[@]}")
PEERS_JSON="[${PEERS_JSON%, }]"

sudo python3 - "$YGG_CONF" "$PEERS_JSON" << 'PYEOF'
import sys, re
conf_path  = sys.argv[1]
peers_json = sys.argv[2]
with open(conf_path) as f:
    content = f.read()
content = re.sub(r'\s*Peers:\s*\[.*?\]', '\n  Peers: ' + peers_json, content, flags=re.DOTALL)
with open(conf_path, 'w') as f:
    f.write(content)
print("  Peers updated.")
PYEOF

info "Enabling and starting Yggdrasil..."
sudo systemctl enable yggdrasil
sudo systemctl restart yggdrasil

info "Waiting for Yggdrasil address..."
YGG_IP=""
for i in $(seq 1 20); do
    YGG_IP=$(ip addr show 2>/dev/null | grep -oP '(?<=inet6 )2[0-9a-f:]+(?=/7)' | head -1)
    [ -n "$YGG_IP" ] && break
    sleep 1
done

if [ -n "$YGG_IP" ]; then
    ok "Yggdrasil up — this node: $YGG_IP"
else
    warn "Yggdrasil started but address not visible yet (normal on first launch)."
    YGG_IP="(pending — check with: ip addr show | grep '/7')"
fi

# ── RNode ─────────────────────────────────────────────────────────────────────
hdr "RNode Configuration"
USE_RNODE=false
RNODE_PORT=""

read -rp "  Do you have an RNode LoRa radio? [y/N]: " yn
if [[ "$yn" =~ ^[Yy] ]]; then
    DETECTED=""
    for p in /dev/ttyUSB0 /dev/ttyUSB1 /dev/ttyACM0 /dev/ttyACM1; do
        [ -e "$p" ] && { DETECTED="$p"; break; }
    done
    if [ -n "$DETECTED" ]; then
        info "Detected: $DETECTED"
        read -rp "  RNode port [$DETECTED]: " user_port
        RNODE_PORT="${user_port:-$DETECTED}"
    else
        read -rp "  RNode port (e.g. /dev/ttyUSB0): " RNODE_PORT
    fi
    if [ -n "$RNODE_PORT" ]; then
        USE_RNODE=true
        ok "RNode will be configured on $RNODE_PORT"
    else
        warn "No port entered — skipping RNode."
    fi
else
    info "Skipping RNode."
fi

# ── I2P ───────────────────────────────────────────────────────────────────────
hdr "I2P Configuration"
USE_I2P=false

if command -v i2prouter &>/dev/null || command -v i2pd &>/dev/null; then
    if ss -tlnp 2>/dev/null | grep -q 7656; then
        ok "I2P SAM bridge detected on port 7656"
        read -rp "  Enable I2P interface for TOCS? [Y/n]: " yn
        [[ ! "$yn" =~ ^[Nn] ]] && USE_I2P=true
    else
        warn "I2P found but SAM bridge not active."
        echo "    Java I2P: enable SAM at http://127.0.0.1:7657/configclients"
        echo "    i2pd:     set 'enabled = true' under [sam] in /etc/i2pd/i2pd.conf"
        read -rp "  Enable I2P anyway? [y/N]: " yn
        [[ "$yn" =~ ^[Yy] ]] && USE_I2P=true
    fi
else
    info "No I2P router found — skipping."
    echo "    Java I2P: https://geti2p.net"
    echo "    i2pd:     sudo apt install i2pd"
fi

# ── Reticulum config ──────────────────────────────────────────────────────────
hdr "Configuring Reticulum"
mkdir -p "$RNS_CONFIG_DIR"
RNS_CONF="$RNS_CONFIG_DIR/config"

I2P_BLOCK=""
[ "$USE_I2P" = true ] && I2P_BLOCK="
  [[I2P Interface]]
    type = I2PInterface
    enabled = yes
    peer_name = tocs_i2p
    connectable = yes
"

RNODE_BLOCK=""
[ "$USE_RNODE" = true ] && RNODE_BLOCK="
  # RNode LoRa — 915 MHz defaults. Use 'RNode Config' in TOCS to sync from server.
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

cat > "$RNS_CONF" << RNSEOF
# Reticulum config — generated by TOCS Client setup.sh

[reticulum]
  enable_transport = False
  share_instance = Yes
  instance_name = default

[logging]
  loglevel = 2

[interfaces]

  # LAN discovery
  [[Local]]
    type = AutoInterface
    enabled = yes

  # TOCS Server via Yggdrasil
  [[TOCS Server (Yggdrasil)]]
    type = TCPClientInterface
    enabled = yes
    target_host = $SERVER_YGGDRASIL_IP
    target_port = $SERVER_RNS_PORT
${I2P_BLOCK}${RNODE_BLOCK}
RNSEOF

ok "Reticulum config written to $RNS_CONF"

# ── Launcher ──────────────────────────────────────────────────────────────────
hdr "Creating Launch Script"
LAUNCHER="$SCRIPT_DIR/tocs_client.sh"
cat > "$LAUNCHER" << LAUNCHEOF
#!/bin/bash
cd "\$(dirname "\$0")"
venv/bin/python main.py --rns-config "$RNS_CONFIG_DIR" "\$@"
LAUNCHEOF
chmod +x "$LAUNCHER"
ok "Launcher created: $LAUNCHER"

# ── Done ──────────────────────────────────────────────────────────────────────
hdr "Setup Complete"
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
