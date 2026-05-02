#!/usr/bin/env bash

echo "Killing Wolfram kernels..."

ps -W | grep -iE 'WolframKernel|MathKernel' | grep -v grep | awk '{print $4}' |
while read -r pid; do
  echo "Killing Windows PID $pid"
  taskkill //F //PID "$pid"
done

echo "Done."