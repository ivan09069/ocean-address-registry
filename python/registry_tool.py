#!/usr/bin/env python3
"""
Address Registry Toolkit (read-only)

- Loads addresses.json
- Validates basic shape + EVM address format
- Resolves contract addresses by chainId or network key
- Optionally verifies deployed bytecode exists via eth_getCode (no ABIs needed)
"""
from __future__ import annotations
import json, os, re, sys, argparse, urllib.request, urllib.error
from typing import Any, Dict, Optional, Tuple

ADDR_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")

def load_registry(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _is_addr(x: Any) -> bool:
    return isinstance(x, str) and bool(ADDR_RE.match(x))

def validate_registry(reg: Dict[str, Any]) -> Tuple[bool, str]:
    if not isinstance(reg, dict) or not reg:
        return False, "Top-level must be a non-empty object of networks"
    for net, cfg in reg.items():
        if not isinstance(cfg, dict):
            return False, f"Network '{net}' must be an object"
        if "chainId" not in cfg or not isinstance(cfg["chainId"], int) or cfg["chainId"] <= 0:
            return False, f"Network '{net}' missing valid chainId"
        if "startBlock" not in cfg or not isinstance(cfg["startBlock"], int) or cfg["startBlock"] < 0:
            return False, f"Network '{net}' missing valid startBlock"
        for k, v in cfg.items():
            if k in ("chainId", "startBlock"):
                continue
            if isinstance(v, str):
                # allow non-address strings, but warn by returning message; treat as hard fail here for safety.
                if not _is_addr(v):
                    return False, f"Network '{net}' field '{k}' is not an EVM address: {v}"
            elif isinstance(v, dict):
                for vk, vv in v.items():
                    if not _is_addr(vv):
                        return False, f"Network '{net}' field '{k}.{vk}' is not an EVM address: {vv}"
            else:
                # allow other types if needed, but keep strict by default
                return False, f"Network '{net}' field '{k}' has unsupported type {type(v).__name__}"
    return True, "OK"

def find_network_by_chainid(reg: Dict[str, Any], chain_id: int) -> Optional[str]:
    for net, cfg in reg.items():
        if isinstance(cfg, dict) and cfg.get("chainId") == chain_id:
            return net
    return None

def get_address(reg: Dict[str, Any], chain: str | int, name: str, template_id: Optional[str] = None) -> str:
    if isinstance(chain, int):
        net = find_network_by_chainid(reg, chain)
        if not net:
            raise KeyError(f"chainId {chain} not found in registry")
    else:
        net = chain
        if net not in reg:
            raise KeyError(f"network '{net}' not found")
    cfg = reg[net]
    if template_id is None:
        val = cfg.get(name)
        if not isinstance(val, str):
            raise KeyError(f"{net}.{name} not found or not a string")
        return val
    tmpl = cfg.get(name)
    if not isinstance(tmpl, dict):
        raise KeyError(f"{net}.{name} is not a template map")
    val = tmpl.get(str(template_id))
    if not isinstance(val, str):
        raise KeyError(f"{net}.{name}.{template_id} not found")
    return val

def rpc_call(url: str, method: str, params: list) -> Any:
    payload = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def has_code(url: str, address: str) -> bool:
    r = rpc_call(url, "eth_getCode", [address, "latest"])
    code = r.get("result")
    return isinstance(code, str) and code not in ("0x", "0x0")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default=os.path.join(os.path.dirname(__file__), "..", "addresses.json"))
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("validate")

    rp = sub.add_parser("resolve")
    rp.add_argument("--chain", required=True, help="network key (e.g. base) OR chainId (e.g. 8453)")
    rp.add_argument("--name", required=True, help="contract name (e.g. Router, Ocean, ERC20Template)")
    rp.add_argument("--template-id", default=None, help="template id for template maps")

    vp = sub.add_parser("verify")
    vp.add_argument("--rpc", required=True, help="RPC URL for the target chain")
    vp.add_argument("--chain", required=True, help="network key OR chainId")
    vp.add_argument("--names", nargs="*", default=[], help="optional list of contract names to verify; default verifies all string addresses")

    args = ap.parse_args()
    reg = load_registry(args.registry)

    if args.cmd == "validate":
        ok, msg = validate_registry(reg)
        print(msg)
        return 0 if ok else 2

    if args.cmd == "resolve":
        chain = int(args.chain) if args.chain.isdigit() else args.chain
        addr = get_address(reg, chain, args.name, args.template_id)
        print(addr)
        return 0

    if args.cmd == "verify":
        chain = int(args.chain) if args.chain.isdigit() else args.chain
        net = chain if isinstance(chain, str) else find_network_by_chainid(reg, chain)
        if not net or (isinstance(chain, str) and chain not in reg):
            print("Unknown chain/network", file=sys.stderr)
            return 2
        cfg = reg[net] if isinstance(chain, str) else reg[net]  # type: ignore[index]
        targets = []
        if args.names:
            for n in args.names:
                v = cfg.get(n)
                if isinstance(v, str):
                    targets.append((n, v))
                elif isinstance(v, dict):
                    for tid, vv in v.items():
                        if isinstance(vv, str):
                            targets.append((f"{n}.{tid}", vv))
        else:
            for k, v in cfg.items():
                if k in ("chainId", "startBlock"):
                    continue
                if isinstance(v, str):
                    targets.append((k, v))
                elif isinstance(v, dict):
                    for tid, vv in v.items():
                        if isinstance(vv, str):
                            targets.append((f"{k}.{tid}", vv))

        bad = 0
        for name, addr in targets:
            try:
                ok = has_code(args.rpc, addr)
            except Exception as e:
                ok = False
            status = "OK" if ok else "MISSING_CODE"
            print(f"{name}\t{addr}\t{status}")
            if not ok:
                bad += 1
        return 0 if bad == 0 else 3

    return 2

if __name__ == "__main__":
    raise SystemExit(main())
