#!/bin/bash
echo "Installing dependencies..."
pip install -r requirements.txt
echo "Starting Rewoon..."
python3 rewoon.py
