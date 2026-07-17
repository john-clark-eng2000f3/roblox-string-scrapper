import argparse
import json
import os
import sys
from pathlib import Path
from roblox_string_scrapper.reader import RbxReader
from roblox_string_scrapper.extractor import (
    extract_raw_strings,
    extract_remotes,
    extract_urls,
    extract_scripts,
)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="roblox-strings",
        description="Extract raw strings, Remotes, URLs, and Lua scripts from binary .rbxl/.rbxm files.",
    )
    parser.add_argument("file", type=Path, help="Path to .rbxl or .rbxm file")
    parser.add_argument(
        "-m",
        "--min-len",
        dest="min_length",
        type=int,
        default=4,
        help="Minimum length for raw strings (default: 4)",
    )
    parser.add_argument(
        "-t",
        "--type",
        choices=["all", "strings", "remotes", "urls", "scripts"],
        default="all",
        help="Filter extraction target (default: all)",
    )
    parser.add_argument(
        "--dump-scripts",
        type=Path,
        metavar="DIR",
        help="Directory to dump extracted Lua/Luau scripts to disk",
    )
    parser.add_argument(
        "--no-dedup",
        action="store_true",
        help="Do not deduplicate extracted string lists",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON to stdout",
    )
    return parser


def _write_scripts_to_dir(scripts, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    used_names = {}
    for s in scripts:
        raw_name = s.get("name") or "unnamed"
        # sanitize path characters from roblox instance names
        safe_name = "_".join(raw_name.split("/")).replace("\\", "_")
        count = used_names.get(safe_name, 0)
        used_names[safe_name] = count + 1
        filename = f"{safe_name}_{count}.lua" if count > 0 else f"{safe_name}.lua"
        
        target_path = out_dir / filename
        source = s.get("source", "")
        target_path.write_text(source, encoding="utf-8", errors="replace")


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.file.is_file():
        sys.stderr.write(f"error: '{args.file}' does not exist or is not a file\n")
        return 1

    try:
        reader = RbxReader(args.file)
        parsed = reader.parse()
    except Exception as exc:
        sys.stderr.write(f"error parsing {args.file.name}: {exc}\n")
        return 2

    # print(f"DEBUG: chunks parsed={len(parsed.chunks)}")
    results = {}
    target = args.type
    dedup = not args.no_dedup

    if target in ("all", "strings"):
        results["strings"] = extract_raw_strings(parsed, min_len=args.min_length, dedup=dedup)
    if target in ("all", "remotes"):
        results["remotes"] = extract_remotes(parsed, dedup=dedup)
    if target in ("all", "urls"):
        results["urls"] = extract_urls(parsed, dedup=dedup)
    if target in ("all", "scripts") or args.dump_scripts:
        results["scripts"] = extract_scripts(parsed)

    if args.dump_scripts:
        scripts_list = results.get("scripts", [])
        _write_scripts_to_dir(scripts_list, args.dump_scripts)
        sys.stderr.write(f"dumped {len(scripts_list)} scripts to {args.dump_scripts}\n")
        if target == "scripts" and not args.json:
            return 0

    # avoid broken pipe traceback when piping to head/grep
    try:
        if args.json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
            return 0

        for category, items in results.items():
            if not items:
                continue
            if target == "all":
                print(f"=== {category.upper()} ({len(items)}) ===")
            for item in items:
                if isinstance(item, dict):
                    name = item.get("name", "unknown")
                    cls = item.get("class_name", "Script")
                    sz = len(item.get("source", ""))
                    print(f"[{cls}] {name} ({sz} bytes)")
                else:
                    print(item)
            if target == "all":
                print()
    except BrokenPipeError:
        # devnull stdout to silence python runtime cleanup error on pipe close
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        return 0

    return 0
