# Slack Wins Logger

A Flask application that logs team wins from Slack slash commands.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create a `.env` file** in the project root with your Slack credentials:
   ```
   SLACK_SIGNING_SECRET=your_slack_signing_secret_here
   SLACK_BOT_TOKEN=xoxb-your_bot_token_here
   ```

3. **Get your Slack credentials:**
   - **Signing Secret:** Go to https://api.slack.com/apps → Your App → Basic Information → App Credentials
   - **Bot Token:** Go to https://api.slack.com/apps → Your App → OAuth & Permissions → Bot User OAuth Token

4. **Run the application:**
   ```bash
   python app.py
   ```

## Slack App Configuration

1. Create a Slack app at https://api.slack.com/apps
2. Add a slash command:
   - Command: `/logthiswin`
   - Request URL: `https://your-domain.com/logthiswin`
   - Short description: "Log a team win"
3. Install the app to your workspace
4. Copy the signing secret to your `.env` file

## Usage

Users can log wins using the slash command:
```
/logthiswin Just completed a major milestone!
```

Wins are stored in `win_logs.json` organized by user ID.

## Win Summaries

The app can send weekly win summaries to users via DM.

### Manual Trigger
Send summaries to all users:
```bash
curl -X POST https://your-domain.com/send-summaries
```

### Test DM
Send a test DM to a specific user:
```bash
curl -X POST https://your-domain.com/test-dm \
  -d "user_id=U1234567890"
```

## Security Features

- ✅ Slack signature verification
- ✅ Request timestamp validation (5-minute window)
- ✅ Input validation
- ✅ Proper error handling
- ✅ Environment variable validation 