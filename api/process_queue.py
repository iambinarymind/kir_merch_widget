import os
import requests
import redis
import json
from flask import Flask, request, jsonify
from datetime import datetime, timezone

# This script is intended to be run by a Vercel Cron Job, not as a public endpoint.

# Initialize the Flask application
app = Flask(__name__)

# --- Configuration ---
SE_ACCOUNT_ID = os.environ.get('SE_ACCOUNT_ID')
SE_JWT_TOKEN = os.environ.get('SE_JWT_TOKEN')
SE_PROVIDER_ID = os.environ.get('SE_PROVIDER_ID')
SE_AMOUNT_STR = os.environ.get('SE_AMOUNT')
SE_DISPLAY_NAME = os.environ.get('SE_DISPLAY_NAME')
SE_USERNAME = os.environ.get('SE_USERNAME')
SE_TYPE = os.environ.get('SE_TYPE')

# Vercel KV (Redis) connection
try:
    redis_client = redis.from_url(os.environ.get("KV_URL"))
except redis.exceptions.ConnectionError as e:
    print(f"Could not connect to Vercel KV (Redis): {e}")
    redis_client = None

# StreamElements API endpoint
SE_API_URL = f"https://api.streamelements.com/kappa/v2/activities/{SE_ACCOUNT_ID}"
SALE_QUEUE_KEY = "sale_alert_queue"

@app.route('/process_queue', methods=['GET'])
def process_queue():
    """
    Pops one sale from the queue and sends an alert to StreamElements.
    This endpoint should be protected and only triggered by a Vercel Cron Job.
    """
    # 1. Check for complete server configuration
    if not redis_client:
        return "Error: Vercel KV not connected", 500

    required_vars = [
        SE_ACCOUNT_ID, SE_JWT_TOKEN, SE_PROVIDER_ID,
        SE_AMOUNT_STR, SE_DISPLAY_NAME, SE_USERNAME, SE_TYPE
    ]
    if not all(required_vars):
        print("Error: One or more required environment variables are not set.")
        return "Error: Server configuration incomplete", 500

    # 2. Pop one item from the front of the queue
    try:
        # LPOP is an atomic operation
        sale_data_str = redis_client.lpop(SALE_QUEUE_KEY)
    except redis.exceptions.RedisError as e:
        print(f"Error fetching from queue: {e}")
        return "Error: Failed to access queue", 500

    if not sale_data_str:
        print("Queue is empty. Nothing to process.")
        return "Queue empty", 200

    # The data is stored as a string, so we parse it back to a dictionary
    store_data = json.loads(sale_data_str)
    print("Processing sale from queue:", store_data)

    # 3. Construct and send the payload to StreamElements
    try:
        se_amount = float(SE_AMOUNT_STR)
        message = "Sale Detected!"

        se_payload = {
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "data": { "amount": se_amount, "avatar": "https://cdn.streamelements.com/assets/dashboard/my-overlays/overlay-default-preview-2.jpg", "displayName": SE_DISPLAY_NAME, "username": SE_USERNAME, "providerId": SE_PROVIDER_ID, "gifted": False, "message": message },
            "flagged": False, "provider": "twitch", "isMock": True, "type": SE_TYPE
        }
        se_headers = { "Authorization": f"Bearer {SE_JWT_TOKEN}", "Content-Type": "application/json" }

        response = requests.post(SE_API_URL, headers=se_headers, json=se_payload)
        response.raise_for_status()
        print(f"StreamElements API response: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"An error occurred during processing: {e}")
        # OPTIONAL: If processing fails, you could push the item back to the queue
        # redis_client.rpush(SALE_QUEUE_KEY, sale_data_str)
        return f"Failed to process sale: {e}", 500

    return "Successfully processed one sale from queue", 200
