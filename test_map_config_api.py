#!/usr/bin/env python3
"""Test script to verify map config API endpoint"""

import requests
import json

API_URL = "http://localhost:8788/api/sns/map-config"

try:
    print(f"Testing API endpoint: {API_URL}")
    response = requests.get(API_URL)
    print(f"Status code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"\nAPI Response:")
        print(json.dumps(data, indent=2, ensure_ascii=False))

        if data.get('success') and data.get('data'):
            map_type = data['data'].get('map_type')
            print(f"\nMap type: {map_type} (type: {type(map_type).__name__})")

            if map_type == '0':
                print("✓ Should load Google Map (googlemap3d.html)")
            elif map_type == '1':
                print("✓ Should load Baidu Map (map.html)")
            else:
                print(f"⚠ Unknown map type: {map_type}")
        else:
            print("✗ API returned unsuccessful response")
    else:
        print(f"✗ API returned error status: {response.status_code}")

except requests.exceptions.ConnectionError:
    print("✗ Cannot connect to API server. Is it running?")
    print("  Start it with: python api_server.py")
except Exception as e:
    print(f"✗ Error: {e}")
