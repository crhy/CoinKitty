# CoinKitty Wallet

A desktop crypto wallet for the CoinKitty bounty economy, written in Python
(GTK 4 + libadwaita), packaged as the flatpak `io.github.crhy.CoinKittyWallet`.

> **Demo coins only.** KittyChain does not exist yet. The wallet runs on a
> demo backend with fake balances in a local JSON file. Every coin it shows is
> a demo coin, never real money.

## Run from source

```sh
PYTHONPATH=src python3 -m coinkitty_wallet
```

## Run the tests

```sh
PYTHONPATH=src timeout 120 xvfb-run -a python3 -m unittest discover -s tests
```

## Building the flatpak (owner)

```sh
flatpak-builder --user --install --force-clean build-dir io.github.crhy.CoinKittyWallet.yml
```

## License

MIT, see [LICENSE](LICENSE).
