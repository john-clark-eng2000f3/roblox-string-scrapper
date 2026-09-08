# roblox-string-scrapper

A small CLI tool to pull raw strings, script sources, RemoteEvent names, and rbxassetid URLs directly out of Roblox binary place (`.rbxl`) and model (`.rbxm`) files without having to open Roblox Studio.

I built this because Studio takes forever to open large places when you just want to inspect what remotes exist or grab an asset link someone pasted in a script property.

## Install

```bash
pip install .
```

Or editable for local hacking:

```bash
pip install -e .
```

## Usage

### RemoteEvents and RemoteFunctions

Lists all network instances found in the file along with their hierarchy paths:

```bash
rbx-strings remotes game.rbxl
```

Output as JSON to pipe into jq:

```bash
rbx-strings remotes game.rbxl --json
```

### Embedded Lua Sources

Dumps cleartext source code from `Script`, `LocalScript`, and `ModuleScript` instances into a target folder:

```bash
rbx-strings scripts game.rbxl --out ./unpacked_scripts
```

Keep in mind: published client-side places often ship Luau bytecode instead of raw source. This will only pull sources where `Source` chunk property is intact (like places saved from Studio directly or unstripped models).

### Asset URLs & IDs

Scans string properties for `rbxassetid://`, `roblox.com/asset/?id=`, and raw texture/sound hashes:

```bash
rbx-strings assets model.rbxm
```

### Raw String Scraping

Extracts printable strings from decompression buffers with length filtering and noise exclusion:

```bash
rbx-strings raw game.rbxl --min-len 8 --filter-noise
```

## Limitations

- Binary format only (starts with `<roblox!`). XML format (`.rbxmx` / `.rbxlx`) is not handled here since you can just grep those with standard tools.
- Does not decompile bytecode chunks. If Studio stripped source on publish, you'll see empty script outputs for those instances.

<!-- checked: 2026-09-08 -->
