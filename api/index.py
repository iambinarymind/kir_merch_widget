import os
import redis
import json
from flask import Flask, request, jsonify

# Initialize the Flask application
app = Flask(__name__)

# --- Configuration ---
# Vercel KV (Redis) connection details are automatically provided by Vercel
# when you connect a KV store to your project.
try:
    redis_client = redis.from_url(os.environ.get("KV_URL"))
except redis.exceptions.ConnectionError as e:
    print(f"Could not connect to Vercel KV (Redis): {e}")
    redis_client = None

# The key we will use in Redis for our queue list.
SALE_QUEUE_KEY = "sale_alert_queue"

@app.route('/webhook/sales', methods=['POST'])
def handle_store_sale():
    """
    This endpoint receives a webhook from a store and adds the sale
    data to a queue in Vercel KV for later processing.
    """
    if not redis_client:
        print("Error: Vercel KV not connected. Cannot queue sale.")
        return jsonify({"status": "error", "message": "Server configuration incomplete"}), 500

    # 1. Get the JSON payload from the store webhook
    store_data = request.get_json()
    if not store_data:
        return jsonify({"status": "error", "message": "No data received"}), 400

    print("Received store sale data, adding to queue:", store_data)

    # 2. Add the sale data to the end of the list (queue) in Redis
    try:
        # We store the data as a JSON string
        redis_client.rpush(SALE_QUEUE_KEY, json.dumps(store_data))
    except redis.exceptions.RedisError as e:
        print(f"Error adding sale to queue: {e}")
        return jsonify({"status": "error", "message": "Failed to queue sale notification"}), 500

    # 3. ALWAYS respond to the store with a 200 OK to acknowledge receipt.
    return jsonify({"status": "success", "message": "Sale queued for processing"}), 200

# This allows the script to be run locally for testing if needed
if __name__ == "__main__":
    # Note: Local testing would require a running Redis instance and KV_URL env var.
    app.run(port=5000, debug=True)
