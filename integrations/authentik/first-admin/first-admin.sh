#!/bin/sh
# Create or refresh the first administrator of an authentik instance (P77).
#
#   first-admin.sh <authentik server container> [administrator folder]
#   first-admin.sh --akadmin-only <authentik server container>
#
# --akadmin-only: for an instance whose administrator already exists (for example a
# Google-linked account with a passkey), only make sure akadmin is present and
# switched off. It refuses when no other active administrator has a passkey.
#
# Asks for the administrator's email and name (or reads FIRST_ADMIN_EMAIL and
# FIRST_ADMIN_NAME), confirms, then prints a one-time 24-hour link that registers
# the administrator's passkey. Rerun it to issue a new link. The link is printed
# here only: do not paste it into logs, tickets or Git.
set -eu
umask 077
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
docker=${DOCKER:-docker}
if [ "${1:-}" = --akadmin-only ]; then
    container=${2:?usage: first-admin.sh --akadmin-only <authentik server container>}
    if [ "${FIRST_ADMIN_YES:-}" != 1 ]; then
        printf 'Switch off akadmin on %s (recreated if absent)? [y/N] ' "$container" >/dev/tty
        IFS= read -r answer </dev/tty
        case $answer in y|Y|yes) ;; *) echo 'Cancelled; nothing changed.' >&2; exit 1 ;; esac
    fi
    output=$($docker exec -i -e FIRST_ADMIN_MODE=akadmin-only "$container" ak shell <"$here/first_admin.py" 2>&1) || true
    result=$(printf '%s\n' "$output" | grep '^FIRST_ADMIN_' || true)
    if ! printf '%s\n' "$result" | grep -q '^FIRST_ADMIN_OK '; then
        printf '%s\n' "$result" | grep '^FIRST_ADMIN_ERROR' >&2 || printf '%s\n' "$output" | tail -5 >&2
        exit 1
    fi
    printf '%s\n' "$result" | sed -n 's/^FIRST_ADMIN_OK //p'
    exit 0
fi
container=${1:?usage: first-admin.sh <authentik server container> [administrator folder]}
folder=${2:-${FIRST_ADMIN_PATH:-administrators}}
email=${FIRST_ADMIN_EMAIL:-}
name=${FIRST_ADMIN_NAME:-}

ask() {
    printf '%s' "$1" >/dev/tty
    IFS= read -r reply </dev/tty
    printf '%s' "$reply"
}

if [ -z "$email" ]; then email=$(ask 'Administrator email: '); fi
if [ -z "$name" ]; then name=$(ask 'Administrator name: '); fi
if [ "${FIRST_ADMIN_YES:-}" != 1 ]; then
    answer=$(ask "Create or refresh administrator $email ($name) in $folder, passkey only, and switch off akadmin? [y/N] ")
    case $answer in y|Y|yes) ;; *) echo 'Cancelled; nothing changed.' >&2; exit 1 ;; esac
fi

setting="$here/passkey-providers.json"
[ -e "$setting" ] || setting="$here/../passkey-providers.json"
providers=$(cat "$setting")
set -- -e FIRST_ADMIN_EMAIL="$email" -e FIRST_ADMIN_NAME="$name" -e FIRST_ADMIN_PATH="$folder" \
    -e FIRST_ADMIN_PROVIDERS="$providers"
if [ -n "${FIRST_ADMIN_BASE_URL:-}" ]; then set -- "$@" -e FIRST_ADMIN_BASE_URL="$FIRST_ADMIN_BASE_URL"; fi
output=$($docker exec -i "$@" "$container" ak shell <"$here/first_admin.py" 2>&1) || true
result=$(printf '%s\n' "$output" | grep '^FIRST_ADMIN_' || true)
if ! printf '%s\n' "$result" | grep -q '^FIRST_ADMIN_LINK '; then
    printf '%s\n' "$result" | grep '^FIRST_ADMIN_ERROR' >&2 || printf '%s\n' "$output" | tail -5 >&2
    echo 'The administrator was not set up; nothing was changed.' >&2
    exit 1
fi
printf '%s\n' "$result" | sed -n 's/^FIRST_ADMIN_OK //p'
link=$(printf '%s\n' "$result" | sed -n 's/^FIRST_ADMIN_LINK //p')
cat <<MESSAGE

Send this link to $email over a private channel. It works once and expires in
24 hours. It registers a passkey from Apple Passwords, Bitwarden, Google Password
Manager or Chrome on Mac; after that the administrator signs in with that passkey
only. Rerun this command for a new link.

$link

MESSAGE
