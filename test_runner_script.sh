#!/bin/bash
REPO=$1
COMMIT=$2

source run_or_failed.sh

run_or_failed "Repository folder not found" pushd "$REPO" 1>/dev/null
run_or_failed "Could not clean repository" git clean -d -f -x
run_or_failed "Could not call git pull" git pull
run_or_failed "Could not update to given commit hash" git reset --hard "$COMMIT"
