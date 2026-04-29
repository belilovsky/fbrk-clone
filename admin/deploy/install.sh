#!/bin/bash
# Run on the VPS as root. Idempotent.
set -euo pipefail

ADMIN_DIR=/opt/fbrk-admin
PUBLIC_DIR=/var/www/fbrk.qdev.run
ENV_DIR=/etc/fbrk-admin

apt-get update -qq
apt-get install -y -qq python3-venv python3-pip

# Create app user group (use existing www-data)
install -d -o www-data -g www-data "$ADMIN_DIR"
install -d -o www-data -g www-data "$PUBLIC_DIR/img/uploads/web"
install -d -o www-data -g www-data "$PUBLIC_DIR/img/uploads/thumb"

# Venv + deps
if [ ! -d "$ADMIN_DIR/.venv" ]; then
    python3 -m venv "$ADMIN_DIR/.venv"
fi
"$ADMIN_DIR/.venv/bin/pip" install --upgrade pip -q
"$ADMIN_DIR/.venv/bin/pip" install -q -r "$ADMIN_DIR/requirements.txt"

# Env file (only once — preserve on re-install)
mkdir -p "$ENV_DIR"
if [ ! -f "$ENV_DIR/fbrk-admin.env" ]; then
    JWT_SECRET=$(openssl rand -hex 32)
    API_KEY=$(openssl rand -hex 24)
    cat > "$ENV_DIR/fbrk-admin.env" <<EOF
FBRK_ADMIN_USER=admin
FBRK_ADMIN_PASSWORD=changeme-now
FBRK_JWT_SECRET=$JWT_SECRET
FBRK_API_KEY=$API_KEY
FBRK_DB_PATH=/opt/fbrk-admin/fbrk.db
FBRK_PUBLIC_ROOT=/var/www/fbrk.qdev.run
FBRK_UPLOADS_DIR=/var/www/fbrk.qdev.run/img/uploads
FBRK_UPLOADS_URL=img/uploads
FBRK_DATA_JS=/var/www/fbrk.qdev.run/js/data.js
FBRK_SESSION_DAYS=7
FBRK_COOKIE_SECURE=true
EOF
    chmod 600 "$ENV_DIR/fbrk-admin.env"
    chown root:root "$ENV_DIR/fbrk-admin.env"
fi

# Ensure admin owns its files (SQLite must be writable)
chown -R www-data:www-data "$ADMIN_DIR"
chown -R www-data:www-data "$PUBLIC_DIR/img/uploads"

# systemd unit
cp "$ADMIN_DIR/deploy/fbrk-admin.service" /etc/systemd/system/fbrk-admin.service
systemctl daemon-reload
systemctl enable fbrk-admin
systemctl restart fbrk-admin

sleep 1
systemctl --no-pager status fbrk-admin | head -12

echo "---"
echo "Admin installed. Edit /etc/fbrk-admin/fbrk-admin.env and set FBRK_ADMIN_PASSWORD,"
echo "then: systemctl restart fbrk-admin && rm -f /opt/fbrk-admin/fbrk.db  (to re-seed password)"
