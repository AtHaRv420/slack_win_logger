from flask import Flask, request, jsonify
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()
import hashlib
import hmac
import time
import requests

app = Flask(__name__)

LOG_FILE = "win_logs.json"

# Create log file if it doesn't exist
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w") as f:
        json.dump({}, f)

@app.route('/test', methods=['GET'])
def test():
    return jsonify({"message": "Flask is working!"})

@app.route('/logthiswin', methods=['POST'])
def log_win():
    print("=== REQUEST RECEIVED ===")
    print(f"DEBUG: All headers received: {dict(request.headers)}")
    print(f"DEBUG: Postman-Test header value: '{request.headers.get('Postman-Test')}'")
    print(f"DEBUG: Postman-Test == 'true': {request.headers.get('Postman-Test') == 'true'}")
    
    if request.headers.get('Postman-Test') == 'true':
        print("DEBUG: Entering Postman test mode")
        # Skip signature validation for testing
        user_id = request.form.get('user_id')
        text = request.form.get('text')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        with open(LOG_FILE, 'r') as f:
            logs = json.load(f)

        if user_id not in logs:
            logs[user_id] = []

        logs[user_id].append({
            'message': text,
            'timestamp': timestamp,
            'user_name': 'Postman Tester',
            'channel_id': 'debug'
        })

        with open(LOG_FILE, 'w') as f:
            json.dump(logs, f, indent=2)

        return jsonify({
            "response_type": "ephemeral",
            "text": f"✅ Logged (Postman): *{text}*"
        })
    
    print("DEBUG: Not in Postman test mode, proceeding with Slack verification")
    # Check if signing secret is configured
    slack_signing_secret = os.environ.get("SLACK_SIGNING_SECRET")
    if not slack_signing_secret:
        print("DEBUG: SLACK_SIGNING_SECRET not found in environment")
        return jsonify({
            "response_type": "ephemeral",
            "text": "❌ Server configuration error: SLACK_SIGNING_SECRET not set"
        }), 500

    # Verify Slack signature
    request_body = request.get_data().decode('utf-8')
    timestamp = request.headers.get('X-Slack-Request-Timestamp')
    slack_signature = request.headers.get('X-Slack-Signature')
    
    print(f"DEBUG: Request headers: {dict(request.headers)}")
    print(f"DEBUG: Request body: {request_body}")
    print(f"DEBUG: Timestamp: {timestamp}")
    print(f"DEBUG: Slack signature: {slack_signature}")
    
    # Validate required headers
    if not timestamp or not slack_signature:
        print("DEBUG: Missing required headers")
        return jsonify({
            "response_type": "ephemeral",
            "text": "❌ Missing required Slack headers"
        }), 400

    # Check if request is too old (5 minutes)
    if abs(time.time() - int(timestamp)) > 60 * 5:
        print("DEBUG: Request too old")
        return jsonify({
            "response_type": "ephemeral",
            "text": "❌ Request too old"
        }), 403

    # Verify signature
    sig_basestring = f"v0:{timestamp}:{request_body}"
    my_signature = 'v0=' + hmac.new(
        slack_signing_secret.encode('utf-8'),
        sig_basestring.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    print(f"DEBUG: My signature: {my_signature}")
    print(f"DEBUG: Slack signature: {slack_signature}")
    print(f"DEBUG: Signatures match: {hmac.compare_digest(my_signature, slack_signature)}")

    if not hmac.compare_digest(my_signature, slack_signature):
        print("DEBUG: Invalid signature")
        return jsonify({
            "response_type": "ephemeral",
            "text": "❌ Invalid signature"
        }), 403

    try:
        # Validate required form data
        user_id = request.form.get('user_id')
        user_name = request.form.get('user_name')
        text = request.form.get('text')
        channel_id = request.form.get('channel_id')
        
        if not user_id or not text:
            return jsonify({
                "response_type": "ephemeral",
                "text": "❌ Missing required fields: user_id and text are required"
            }), 400

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Read existing logs
        with open(LOG_FILE, 'r') as f:
            logs = json.load(f)

        # Append new win
        if user_id not in logs:
            logs[user_id] = []

        logs[user_id].append({
            'message': text,
            'timestamp': timestamp,
            'channel_id': channel_id,
            'user_name': user_name
        })

        # Save updated logs
        with open(LOG_FILE, 'w') as f:
            json.dump(logs, f, indent=2)

        return jsonify({
            "response_type": "ephemeral",
            "text": f"✅ Logged your win: *{text}*"
        })

    except Exception as e:
        print("Incoming Slack request:", request.form)
        return jsonify({
            "response_type": "ephemeral",
            "text": f"❌ Failed to log your win: {str(e)}"
        }), 500

def send_slack_dm(user_id, message):
    """Send a direct message to a Slack user"""
    slack_token = os.environ.get("SLACK_BOT_TOKEN")
    if not slack_token:
        print("ERROR: SLACK_BOT_TOKEN not set")
        return False
    
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {slack_token}",
        "Content-Type": "application/json"
    }
    data = {
        "channel": user_id,
        "text": message,
        "unfurl_links": False
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        if result.get("ok"):
            print(f"✅ DM sent to {user_id}")
            return True
        else:
            print(f"❌ Failed to send DM to {user_id}: {result.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Error sending DM to {user_id}: {str(e)}")
        return False

def generate_win_summary(user_id, wins):
    """Generate a formatted summary of wins for a user"""
    if not wins:
        return "You haven't logged any wins yet! Use `/logthiswin` to log your first win."
    
    summary = f"🎉 *Your Wins Summary*\n\n"
    
    for i, win in enumerate(wins, 1):
        timestamp = win.get('timestamp', 'Unknown time')
        message = win.get('message', 'No message')
        summary += f"{i}. *{message}*\n   _{timestamp}_\n\n"
    
    summary += f"Total wins: {len(wins)} 🏆"
    return summary

@app.route('/send-summaries', methods=['POST'])
def send_summaries():
    """Manually trigger sending win summaries to all users"""
    try:
        # Read existing logs
        with open(LOG_FILE, 'r') as f:
            logs = json.load(f)
        
        if not logs:
            return jsonify({
                "message": "No wins logged yet",
                "users_notified": 0
            })
        
        users_notified = 0
        
        for user_id, wins in logs.items():
            if wins:  # Only send if user has wins
                summary = generate_win_summary(user_id, wins)
                if send_slack_dm(user_id, summary):
                    users_notified += 1
        
        return jsonify({
            "message": f"Win summaries sent to {users_notified} users",
            "users_notified": users_notified
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to send summaries: {str(e)}"
        }), 500

@app.route('/test-dm', methods=['POST'])
def test_dm():
    """Test endpoint to send a DM to a specific user"""
    user_id = request.form.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    
    message = "🧪 This is a test message from your wins logger!"
    success = send_slack_dm(user_id, message)
    
    return jsonify({
        "success": success,
        "message": "Test DM sent" if success else "Failed to send test DM"
    })

if __name__ == '__main__':
    app.run(debug=True, port=8000)
