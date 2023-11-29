from flask import Flask, request, jsonify,render_template
import json
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

scheduler = BackgroundScheduler()
scheduler.start()

# Function to reset daily quotas
def reset_daily_quotas():
    for key in API_KEYS:
        tipe = API_KEYS[key].get('tipe', '')
        API_KEYS[key]['api_quota'] = SUBSCRIBE.get(tipe, {}).get('BASIC', 0)
        API_KEYS[key]['api_quota'] = SUBSCRIBE.get(tipe, {}).get('ULTIMATE', 0)
        API_KEYS[key]['api_quota'] = SUBSCRIBE.get(tipe, {}).get('PLATINUM', 0)

# Load API keys, quotas, and last reset times from data.json
with open('data.json', 'r') as file:
    data = json.load(file)
scheduler.add_job(reset_daily_quotas, 'cron', hour=0, minute=0)
API_KEYS = data.get('api_amz', {})

SUBSCRIBE = {
    value.get('tipe', ''): {
        "BASIC": 200000,
        "ULTIMATE": 500000,
        "PLATINUM": 1000000
    }
    for _, value in data.get('api_amz', {}).items()
}

@app.route('/verify', methods=['POST'])
def verify_api():
    data = request.form
    api_key = data.get('api_key')
    quota_reset = data.get('reset_time')
    expiration_date = data.get('expiration_date')

    if api_key and api_key in API_KEYS:
        # Check if it's time to reset quota
        if quota_reset == API_KEYS[api_key].get('reset_time', ''):
            API_KEYS[api_key]['api_quota'] = SUBSCRIBE.get(API_KEYS[api_key].get('tipe', ''), {}).get('BASIC', 0)

        # Check if the key is expired
        current_date = datetime.now()
        expiration_date = datetime.strptime(expiration_date, "%Y-%m-%d") if expiration_date else None
        if expiration_date and current_date > expiration_date:
            return jsonify({'error': 'API key expired'}), 403

        # Write the updated data back to the file
        with open('data/data.json', 'w') as file:
            json.dump({'api_amz': API_KEYS}, file)

        return jsonify({'status': 'success'})
    else:
        return jsonify({'error': 'Invalid API key'}), 403
    
@app.route('/')
def landing_page():
    return render_template('halaman/index.html')

@app.route('/amz-email', methods=['POST'])
def verify_email():
    data = request.form
    api_key = data.get('api_key')
    api_quota = data.get('api_quota')

    if api_key and api_key in API_KEYS:
        # Deduct from the daily quota
        remaining_quota = API_KEYS[api_key]['api_quota']
        if remaining_quota > 0:
            API_KEYS[api_key]['api_quota'] -= 1

            # Write the updated data back to the file
            with open('data/data.json', 'w') as file:
                json.dump({'api_amz': API_KEYS}, file)

            # Get expiration date from API_KEYS
            expiration_date = datetime.strptime(API_KEYS[api_key].get('expiration_date', ''), "%Y-%m-%d") if API_KEYS[api_key].get('expiration_date', '') else None

            return jsonify({
                'status': 'success',
                'remaining_quota': remaining_quota,
                'remaining_days': (expiration_date - datetime.now()).days if expiration_date else 0
            })
        else:
            return jsonify({'error': 'Daily quota exceeded'}), 403
    else:
        return jsonify({'error': 'Invalid API key'}), 403

if __name__ == "__main__":
    app.run(debug=True)
