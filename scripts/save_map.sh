#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: ./scripts/save_map.sh <map_name>" >&2
  exit 2
fi

map_name="$1"
if [[ ! "$map_name" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "Refusing unsafe map name: $map_name" >&2
  exit 2
fi

workspace_root="$(cd "$(dirname "$0")/.." && pwd)"
maps_dir="$workspace_root/maps"
mkdir -p "$maps_dir"

base_path="$maps_dir/$map_name"
yaml_path="${base_path}.yaml"
pgm_path="${base_path}.pgm"

echo "Saving map to:"
echo "  $yaml_path"
echo "  $pgm_path"

ros2 run nav2_map_server map_saver_cli -f "$base_path"

if [[ ! -f "$yaml_path" || ! -f "$pgm_path" ]]; then
  echo "Map save failed: expected files were not created." >&2
  exit 1
fi

echo "Map saved successfully."
