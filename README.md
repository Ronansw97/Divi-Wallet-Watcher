# Divi Wallet Watcher

A Discord bot that monitors Divi staker wallets and sends real-time alerts whenever rewards are received.

## Features
- Monitors Divi staker wallets.
- Sends alerts to Discord when rewards are received.
- Integrates with MongoDB for wallet management.

## Requirements
- Python 3.x
- `discord.py`
- `pymongo`
- `requests`

## Setup
1. Clone this repository:

   git clone https://github.com/Ronansw97/Divi-Wallet-Watcher.git

2. Install dependencies:

   pip install -r requirements.txt

3. Configure environment variables in a `.env` file:
   DISCORD_TOKEN=your_discord_bot_token
   ADMIN_USER_ID=your_admin_user_id
   WEBHOOK_URL=your_webhook_url
   MONGO_URI=mongodb://localhost:27017/
   CRYPTOID_API_KEY=your_crypto_id_api_key


4. Run the bot:

   python code.py


## License
This project is licensed under the MIT License.
