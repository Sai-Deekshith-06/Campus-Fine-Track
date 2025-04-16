#!/bin/bash

export dir_path="c:/Desktop/RTFP/new"         # change the path to project where it is residing from root

cd "$dir_path"

# Create virtual environment (first time only)
if [ ! -d "venv" ]; then
  python -m venv venv
  echo "Virtual environment created."
else
  echo "Virtual environment already exists."
fi

# Activate virtual environment (if not already activated)
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Virtual environment not active. Activating..."
    source venv/Scripts/activate
    echo "Virtual environment is actived"
fi
if [ ! -z "$VIRTUAL_ENV" ]; then
    echo "Virtual environment is actived"
fi

# ./setup.sh