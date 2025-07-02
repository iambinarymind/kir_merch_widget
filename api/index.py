import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime, timezone

# Initialize the Flask application
app = Flask(__name__)

# --- Configuration ---
# Fetch sensitive data from environment variables for security.
# In Vercel, you will set these in the project's "Environment Variables" settings.
SE_ACCOUNT_ID = os.environ.get('SE_ACCOUNT_ID')
SE_JWT_TOKEN = os.environ.get('SE_JWT_TOKEN')
SE_PROVIDER_ID = os.environ.get('SE_PROVIDER_ID') # NEW: Provider ID from environment

# StreamElements API endpoint
SE_API_URL = f"https://api.streamelements.com/kappa/v2/activities/{SE_ACCOUNT_ID}"

@app.route('/webhook/sales', methods=['POST'])
def handle_store_sale():
    """
    This endpoint receives a webhook from a store, processes the data,
    and triggers a StreamElements widget overlay.
    """
    # 1. Check if required environment variables are set
    if not SE_ACCOUNT_ID or not SE_JWT_TOKEN or not SE_PROVIDER_ID:
        print("Error: StreamElements Account ID, JWT Token, or Provider ID not set in environment variables.")
        # Return a 500 error but don't break the flow for the store
        return jsonify({"status": "error", "message": "Server configuration incomplete"}), 500

    # 2. Get the JSON payload from the store webhook
    store_data = request.get_json()
    if not store_data:
        return jsonify({"status": "error", "message": "No data received"}), 400

    print("Received store sale data:", store_data)

    # --- You can customize the message based on store data here ---
    # For example, you could extract the customer's name or the total price.
    # customer_name = store_data.get('customer', {}).get('first_name', 'A Customer')
    # total_price = store_data.get('total_price', 'a certain amount')
    # message = f"New sale from {customer_name} for ${total_price}!"
    message = "Sale Detected!" # Default message

    # 3. Construct the payload for the StreamElements API
    se_payload = {
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "data": {
            "amount": 0.10,  # This value is fixed as per your request
            "avatar": "https://cdn.streamelements.com/assets/dashboard/my-overlays/overlay-default-preview-2.jpg",
            "displayName": "KirscheSale",
            "username": "KirscheSale",
            "providerId": SE_PROVIDER_ID, # UPDATED: Using environment variable
            "gifted": False,
            "message": message
        },
        "flagged": False,
        "provider": "twitch",
        "isMock": True,  # This is fixed as per your request
        "type": "tip"
    }

    # 4. Prepare the headers for the StreamElements API request
    se_headers = {
        "Authorization": f"Bearer {SE_JWT_TOKEN}",
        "Content-Type": "application/json"
    }

    # 5. Send the request to StreamElements
    try:
        print("Sending payload to StreamElements...")
        response = requests.post(SE_API_URL, headers=se_headers, json=se_payload)
        response.raise_for_status()  # This will raise an exception for HTTP error codes (4xx or 5xx)
        print(f"StreamElements API response: {response.status_code} - {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"Error sending request to StreamElements: {e}")
        # Even if this fails, we will still send a 200 OK to the store below.

    # 6. ALWAYS respond to the store with a 200 OK to acknowledge receipt.
    # If you don't, the store will consider the webhook failed and will retry.
    return jsonify({"status": "success", "message": "Webhook received"}), 200

# This allows the script to be run locally for testing if needed
if __name__ == "__main__":
    # To run this locally, you would need to set the environment variables first.
    # Example (in bash/zsh):
    # export SE_ACCOUNT_ID='your_account_id'
    # export SE_JWT_TOKEN='your_jwt_token'
    # export SE_PROVIDER_ID='your_provider_id'
    # python api/index.py
    app.run(port=5000, debug=True)
