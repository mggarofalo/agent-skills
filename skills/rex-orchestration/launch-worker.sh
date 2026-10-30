#!/bin/sh
# Launch a Claude worker in a background tab of the caller's Rex session.
# Usage: launch-worker.sh NAME DIR BRIEF
# Prints "WINDOW_ID BLOCK_ID". Answers Claude's trust-this-folder prompt,
# which otherwise leaves the worker idle until someone notices.
set -eu
name=$1 dir=$2 brief=$3
: "${REX_SESSION:?not in Rex}"
[ -f "$brief" ] || { echo "no brief: $brief" >&2; exit 1; }

ids=$(rex window new -s "$REX_SESSION" "$name" -c "$dir" --focus=false --json \
  -- sh -c 'claude --dangerously-skip-permissions -n "$1" "$(cat "$2")"' sh "$name" "$brief" |
  jq -r '"\(.window_id) \(.block_ids[0])"')
block=${ids#* }

# The prompt appears within a few seconds or not at all.
i=0
while [ $i -lt 20 ]; do
  screen=$(rex capture -s "$REX_SESSION" -b "$block" --trim 2>/dev/null || true)
  if printf '%s' "$screen" | grep -q 'Yes, I trust this folder'; then
    # The default is sometimes "No, exit", so select Yes before confirming.
    if printf '%s' "$screen" | grep -q '❯ Yes, I trust this folder'; then
      rex send-key -s "$REX_SESSION" -b "$block" enter
      break
    fi
    rex send-key -s "$REX_SESSION" -b "$block" down
  fi
  # Claude's input box is up, so there's no prompt to answer.
  printf '%s' "$screen" | grep -qE 'esc to interrupt|bypass permissions' && break
  sleep 1; i=$((i + 1))
done

echo "$ids"
