#!/usr/bin/env bash
# Auto-replace deprecated argument
for f in components/*.py; do
  sed -i 's/use_container_width=True/width="stretch"/g' "$f"
done
