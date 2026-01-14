// Address Registry Resolver (read-only)
// Usage in Node/TS:
//   import { AddressRegistry } from "./registry";
//   const reg = AddressRegistry.fromFile("addresses.json");
//   reg.get("base", "Router");
//   reg.get(8453, "ERC20Template", "1");

import * as fs from "fs";

export type Registry = Record<string, any>;

const ADDR_RE = /^0x[a-fA-F0-9]{40}$/;

export class AddressRegistry {
  private reg: Registry;

  private constructor(reg: Registry) {
    this.reg = reg;
  }

  static fromFile(path: string): AddressRegistry {
    const raw = fs.readFileSync(path, "utf8");
    const reg = JSON.parse(raw);
    const ar = new AddressRegistry(reg);
    ar.validateOrThrow();
    return ar;
  }

  validateOrThrow(): void {
    if (!this.reg || typeof this.reg !== "object") throw new Error("registry must be an object");
    for (const [net, cfg] of Object.entries(this.reg)) {
      if (!cfg || typeof cfg !== "object") throw new Error(`network ${net} must be an object`);
      if (typeof (cfg as any).chainId !== "number" || (cfg as any).chainId <= 0) throw new Error(`network ${net} missing chainId`);
      if (typeof (cfg as any).startBlock !== "number" || (cfg as any).startBlock < 0) throw new Error(`network ${net} missing startBlock`);

      for (const [k, v] of Object.entries(cfg as any)) {
        if (k === "chainId" || k === "startBlock") continue;
        if (typeof v === "string") {
          if (!ADDR_RE.test(v)) throw new Error(`network ${net} field ${k} not an address: ${v}`);
        } else if (v && typeof v === "object") {
          for (const [tid, vv] of Object.entries(v as any)) {
            if (typeof vv !== "string" || !ADDR_RE.test(vv)) throw new Error(`network ${net} field ${k}.${tid} not an address: ${vv}`);
          }
        } else {
          throw new Error(`network ${net} field ${k} unsupported type`);
        }
      }
    }
  }

  private findNetworkByChainId(chainId: number): string | undefined {
    for (const [net, cfg] of Object.entries(this.reg)) {
      if (cfg && typeof cfg === "object" && (cfg as any).chainId === chainId) return net;
    }
    return undefined;
  }

  get(chain: string | number, name: string, templateId?: string | number): string {
    const net = typeof chain === "number" ? this.findNetworkByChainId(chain) : chain;
    if (!net || !this.reg[net]) throw new Error(`unknown chain/network: ${chain}`);
    const cfg = this.reg[net];

    if (templateId === undefined) {
      const v = cfg[name];
      if (typeof v !== "string") throw new Error(`missing ${net}.${name}`);
      return v;
    }

    const m = cfg[name];
    if (!m || typeof m !== "object") throw new Error(`${net}.${name} is not a template map`);
    const v = m[String(templateId)];
    if (typeof v !== "string") throw new Error(`missing ${net}.${name}.${templateId}`);
    return v;
  }

  // Optional: list all resolved targets (flattened)
  list(net: string): Array<{ name: string; address: string }> {
    const cfg = this.reg[net];
    if (!cfg) throw new Error(`unknown network: ${net}`);
    const out: Array<{ name: string; address: string }> = [];
    for (const [k, v] of Object.entries(cfg)) {
      if (k === "chainId" || k === "startBlock") continue;
      if (typeof v === "string") out.push({ name: k, address: v });
      else if (v && typeof v === "object") {
        for (const [tid, vv] of Object.entries(v)) {
          if (typeof vv === "string") out.push({ name: `${k}.${tid}`, address: vv });
        }
      }
    }
    return out;
  }
}
