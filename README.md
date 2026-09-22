# Ocean Address Registry Toolkit

This bundle is generated from your uploaded `address.json` and is intended to be **read-only infrastructure glue**.

Contents:
- `addresses.json` (normalized copy; sorted keys)
- `schemas.address-registry.schema.json` (Draft 2020-12 schema)
- `python/registry_tool.py` (validate, resolve, verify via eth_getCode)
- `typescript/registry.ts` (typed resolver w/ validation)

## Quick start (Python)
```bash
python3 python/registry_tool.py validate
python3 python/registry_tool.py resolve --chain base --name Router
python3 python/registry_tool.py resolve --chain 8453 --name ERC20Template --template-id 1
```

### Verify on-chain bytecode exists (safe, read-only)
```bash
# Example: Base mainnet
python3 python/registry_tool.py verify --rpc $BASE_RPC --chain base
```

## Quick start (TypeScript / Node)
```bash
node -e "const { AddressRegistry } = require('./dist/registry');"
```
If you're using TS directly, import `typescript/registry.ts` into your project.

## Security posture
- This registry contains **no secrets**.
- Treat it as immutable config; load at startup; lock; deny writes.
- For runtime safety, run `verify` once per environment and cache results.

Generated: 2025-12-29T01:14:08.599910Z

## License

Copyright (c) 2026 EchoForge Studios. All rights reserved.
No use or copy is permitted without a written license. See [LICENSE](LICENSE).
