#!/usr/bin/env bash
# storywheel: set up a fresh Debian, Ubuntu or Raspberry Pi OS machine (x86_64 or arm64).
#
#   ./install.sh               install what is missing, then storywheel, then run `storywheel setup`
#   ./install.sh --yes         answer yes to every question (installs LibreOffice, skips Neovide)
#   ./install.sh --dry-run     show what it would do and change nothing
#   ./install.sh URL           install storywheel from a git URL instead of this folder
#
# It needs: python3 (3.9+), pipx, Neovim 0.10+ (the distribution's package is often older: the official release is put in ~/.local),
# git (for `storywheel update`). Optional, and asked about: LibreOffice (.odt and .pdf export), Neovide (a window for the Writer).
set -u

YES=0
DRY=0
SOURCE=""
for arg in "$@"; do
  case "$arg" in
    --yes|-y) YES=1 ;;
    --dry-run|-n) DRY=1 ;;
    -h|--help) sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) SOURCE="$arg" ;;
  esac
done

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="${SOURCE:-$HERE}"
BIN="${STORYWHEEL_INSTALL_BIN:-$HOME/.local/bin}"
OPT="${STORYWHEEL_INSTALL_OPT:-$HOME/.local/opt}"
MIN_NVIM_MINOR=10

say()  { printf '%s\n' "$*"; }
step() { printf '\n== %s\n' "$*"; }
run()  { if [ "$DRY" = 1 ]; then printf '   [dry run] %s\n' "$*"; else "$@"; fi; }
ask()  { # ask "question" default(y|n) -> returns 0 for yes
  local q="$1" d="${2:-y}" a
  if [ "$YES" = 1 ] || [ "$DRY" = 1 ]; then [ "$d" = y ]; return; fi
  read -r -p "   $q [$( [ "$d" = y ] && echo Y/n || echo y/N )] " a || a=""
  a="${a:-$d}"; case "$a" in y|Y|yes) return 0 ;; *) return 1 ;; esac
}
have() { command -v "$1" >/dev/null 2>&1; }
SUDO=""; if [ "$(id -u)" != 0 ]; then SUDO="sudo"; fi
apt_install() { run $SUDO apt-get install -y "$@"; }

# --- what this machine is ------------------------------------------------------------------------------------------------------------------
step "Checking this machine"
OS_ID="unknown"; [ -r /etc/os-release ] && . /etc/os-release && OS_ID="${ID:-unknown}"
ARCH="$(uname -m)"
case "$ARCH" in
  x86_64|amd64) NVIM_ARCH="x86_64"; NEOVIDE_ARCH="x86_64" ;;
  aarch64|arm64) NVIM_ARCH="arm64"; NEOVIDE_ARCH="" ;;
  *) say "   This script knows x86_64 and arm64; this is $ARCH. Install Neovim 0.10+ and pipx yourself, then: pipx install $SOURCE"; exit 1 ;;
esac
case "$OS_ID" in
  debian|ubuntu|raspbian|linuxmint|pop) ;;
  *) say "   This script is for Debian, Ubuntu and Raspberry Pi OS; this is '$OS_ID'. Install python3, pipx, git and Neovim 0.10+ yourself,"
     say "   then:  pipx install $SOURCE   and   storywheel setup"; exit 1 ;;
esac
say "   $OS_ID on $ARCH"
[ "$DRY" = 1 ] && say "   (dry run: nothing will be changed)"
if [ ! -e "$SOURCE/pyproject.toml" ] && [ "${SOURCE#*://}" = "$SOURCE" ] && [ "${SOURCE#*@}" = "$SOURCE" ]; then
  say "   $SOURCE has no pyproject.toml; run this from the storywheel folder, or give a git URL."; exit 1
fi

# --- python, pipx, git ---------------------------------------------------------------------------------------------------------------------
step "Python 3.9 or newer"
if have python3 && python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'; then
  say "   found $(python3 --version)"
else
  say "   installing python3"
  run $SUDO apt-get update
  apt_install python3 python3-venv python3-pip
fi

step "pipx"
if have pipx; then say "   found $(pipx --version)"; else say "   installing pipx"; run $SUDO apt-get update; apt_install pipx; fi
run pipx ensurepath >/dev/null 2>&1 || true

step "git (for storywheel update)"
if have git; then say "   found $(git --version)"; else say "   installing git"; apt_install git; fi

# --- Neovim 0.10+ ------------------------------------------------------------------------------------------------------------------------
nvim_ok() {
  have nvim || return 1
  local v; v="$(nvim --version 2>/dev/null | sed -n '1s/^NVIM v\([0-9]*\)\.\([0-9]*\).*/\1 \2/p')"
  [ -n "$v" ] || return 1
  set -- $v
  [ "$1" -gt 0 ] || [ "$2" -ge "$MIN_NVIM_MINOR" ]
}
step "Neovim 0.10 or newer (the Writer)"
if nvim_ok; then
  say "   found $(nvim --version | head -1)"
else
  have nvim && say "   found $(nvim --version | head -1), which is too old"
  CAND="$(apt-cache policy neovim 2>/dev/null | sed -n 's/^ *Candidate: \([0-9]*\)\.\([0-9]*\).*/\1 \2/p')"
  set -- $CAND
  if [ -n "${CAND:-}" ] && { [ "$1" -gt 0 ] || [ "$2" -ge "$MIN_NVIM_MINOR" ]; }; then
    say "   the distribution has Neovim $1.$2: installing it"
    apt_install neovim
  else
    URL="https://github.com/neovim/neovim/releases/latest/download/nvim-linux-${NVIM_ARCH}.tar.gz"
    say "   the distribution's Neovim is older than 0.10: fetching the official release into $OPT"
    say "   $URL"
    run mkdir -p "$OPT" "$BIN"
    if [ "$DRY" = 1 ]; then
      say "   [dry run] download, unpack to $OPT/nvim-linux-${NVIM_ARCH}, link $BIN/nvim"
    else
      TMP="$(mktemp -d)"
      if ! ( have curl && curl -fL --progress-bar -o "$TMP/nvim.tgz" "$URL" ) && ! ( have wget && wget -O "$TMP/nvim.tgz" "$URL" ); then
        say "   could not download Neovim (is curl or wget installed, and are you online?). Install Neovim 0.10+ and run this again."; exit 1
      fi
      rm -rf "$OPT/nvim-linux-${NVIM_ARCH}"
      tar -xzf "$TMP/nvim.tgz" -C "$OPT" && ln -sf "$OPT/nvim-linux-${NVIM_ARCH}/bin/nvim" "$BIN/nvim"
      rm -rf "$TMP"
      say "   installed $("$BIN/nvim" --version | head -1) at $BIN/nvim"
      case ":$PATH:" in *":$BIN:"*) ;; *) say "   note: $BIN is not on your PATH yet; open a new terminal after this script (pipx ensurepath adds it)." ;; esac
    fi
  fi
fi

# --- optional ------------------------------------------------------------------------------------------------------------------------------
step "LibreOffice (optional: .odt and .pdf export; Word .docx export does not need it)"
if have soffice || have libreoffice; then
  say "   found"
elif ask "Install LibreOffice Writer now?" y; then
  apt_install libreoffice-writer
else
  say "   skipped. Later:  sudo apt install libreoffice-writer"
fi

step "Neovide (optional: a window of its own for the Writer, with real line spacing)"
if have neovide; then
  say "   found"
elif [ -z "$NEOVIDE_ARCH" ]; then
  say "   no ready-made build for $ARCH. Optional, from source:  cargo install neovide"
elif ask "Download Neovide into $BIN now?" n; then
  URL="https://github.com/neovide/neovide/releases/latest/download/neovide-linux-${NEOVIDE_ARCH}.tar.gz"
  run mkdir -p "$BIN"
  if [ "$DRY" = 1 ]; then say "   [dry run] $URL"; else
    TMP="$(mktemp -d)"
    if curl -fL --progress-bar -o "$TMP/n.tgz" "$URL" && tar -xzf "$TMP/n.tgz" -C "$TMP" && find "$TMP" -name neovide -type f | head -1 | xargs -I{} install -m 755 {} "$BIN/neovide"; then
      say "   installed $BIN/neovide (it needs a graphical session)"
    else
      say "   could not fetch Neovide; skipped (optional)."
    fi
    rm -rf "$TMP"
  fi
else
  say "   skipped (optional)"
fi

# --- storywheel ----------------------------------------------------------------------------------------------------------------------------
step "storywheel"
run pipx install --force "$SOURCE"
export PATH="$BIN:$HOME/.local/bin:$PATH"
if [ "$DRY" = 1 ]; then
  say "   [dry run] storywheel setup"
else
  have storywheel || { say "   storywheel was installed but is not on PATH yet. Open a new terminal and run:  storywheel setup"; exit 0; }
  say "   $(storywheel --version)"
  [ -d "$SOURCE/.git" ] && storywheel update --record >/dev/null 2>&1      # remember which commit this is, so `storywheel update` notices fixes without a version bump
  step "Setup (a few questions; everything can be changed later in Settings, F4)"
  if [ "$YES" = 1 ]; then storywheel setup --defaults; else storywheel setup; fi
fi
step "Done"
say "   Start writing with:  storywheel"
say "   Later, to get a newer version:  storywheel update"
