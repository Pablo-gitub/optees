#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "Usage: $0 VERSION PYINSTALLER_DIR OUTPUT_DEB" >&2
  exit 2
fi

version="$1"
source_dir="$(readlink -f "$2")"
output_deb="$(readlink -m "$3")"
package_root="$(mktemp -d)"
trap 'rm -rf "${package_root}"' EXIT

if [[ ! -x "${source_dir}/optees" ]]; then
  echo "The PyInstaller directory does not contain an executable optees binary." >&2
  exit 1
fi

install -d \
  "${package_root}/DEBIAN" \
  "${package_root}/opt/optees" \
  "${package_root}/usr/bin" \
  "${package_root}/usr/share/applications" \
  "${package_root}/usr/share/icons/hicolor/256x256/apps"

cp -a "${source_dir}/." "${package_root}/opt/optees/"

ln -s /opt/optees/optees "${package_root}/usr/bin/optees"
ln -s /opt/optees/optees-server "${package_root}/usr/bin/optees-server"
ln -s /opt/optees/optees-mcp "${package_root}/usr/bin/optees-mcp"

install -m 0644 src/optees/assets/logo/dark/appicon_256.png \
  "${package_root}/usr/share/icons/hicolor/256x256/apps/optees.png"

cat > "${package_root}/usr/share/applications/optees.desktop" <<'EOF'
[Desktop Entry]
Name=Optees
Comment=Local optimization toolkit for people and software agents
Exec=/usr/bin/optees
Icon=optees
Terminal=false
Type=Application
Categories=Science;Math;Education;
StartupNotify=true
EOF

installed_size="$(du -sk "${package_root}/opt/optees" | cut -f1)"
cat > "${package_root}/DEBIAN/control" <<EOF
Package: optees
Version: ${version}
Section: science
Priority: optional
Architecture: amd64
Installed-Size: ${installed_size}
Maintainer: Paolo Pietrelli <pablos3339@gmail.com>
Homepage: https://optees.it
Depends: libc6, libdbus-1-3, libegl1, libfontconfig1, libgl1, libxkbcommon-x11-0, libxcb-cursor0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-randr0, libxcb-render-util0, libxcb-shape0, libxcb-xfixes0, libxcb-xinerama0, xdg-utils
Description: Local optimization toolkit for people and software agents
 Optees provides a desktop interface, validated solver contracts, a local REST
 service, and an MCP stdio companion from the same packaged runtime.
EOF

mkdir -p "$(dirname "${output_deb}")"
dpkg-deb --root-owner-group --build "${package_root}" "${output_deb}"
