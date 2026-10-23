#!/bin/sh
export PYTHONPATH=/app/lib/coinkitty-wallet
exec python3 -m coinkitty_wallet "$@"
