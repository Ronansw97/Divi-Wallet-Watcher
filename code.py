import discord
from pymongo import MongoClient
from decimal import Decimal
import asyncio
import requests
import os
import json
import time
import random

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
ADMIN_USER_ID = os.getenv('ADMIN_USER_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# Set up intents and initialize Discord client
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# MongoDB connection
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['your_database']
wallets_collection = db['wallets']

CRYPTOID_API_KEY = os.getenv('CRYPTOID_API_KEY')

# API URLS
WALLET_API_URL = f'https://chainz.cryptoid.info/divi/api.dws?q=getbalance&a={{wallet_id}}&key={CRYPTOID_API_KEY}'
DIVI_PRICE_URL = f'https://chainz.cryptoid.info/divi/api.dws?q=ticker.usd&key={CRYPTOID_API_KEY}'
RICH_LIST_URL = f'https://chainz.cryptoid.info/divi/api.dws?q=rich&key={CRYPTOID_API_KEY}'


async def send_error_to_webhook(error_message):
    """Send errors to the webhook for logging purposes."""
    try:
        error_log = {
            "content": f"🚨 **Error**: {error_message}"
        }
        requests.post(WEBHOOK_URL, data=json.dumps(error_log), headers={"Content-Type": "application/json"})
    except Exception as e:
        print(f"Failed to send error to webhook: {str(e)}")

async def send_webhook_log(user, action):
    # Print the user ID for debugging
    print(f"Logging action for user ID: {user.id}")

    # If the action is performed by the admin, skip logging to the webhook
    if user.id == ADMIN_USER_ID:
        print(f"Skipping logging for admin user: {user.name}#{user.discriminator}")
        return

    # Log message content with username and discriminator
    log_message = {
        "content": f"User `{user.name}#{user.discriminator}` performed action: {action}"
    }

    # Send the log to the Discord webhook
    response = requests.post(WEBHOOK_URL, data=json.dumps(log_message), headers={"Content-Type": "application/json"})
    if response.status_code == 204:
        print(f"Successfully sent log to the webhook: User {user.name}#{user.discriminator} - {action}")
    else:
        print(f"Failed to send log to the webhook: {response.status_code} - {response.text}")


async def get_wallet_value(wallet_id, retries=3):
    for attempt in range(retries):
        try:
            response = requests.get(WALLET_API_URL.format(wallet_id=wallet_id), timeout=10)
            response.raise_for_status()
            return Decimal(response.text)
        except requests.exceptions.Timeout:
            await send_error_to_webhook(f"Timeout error on attempt {attempt + 1} for wallet {wallet_id}.")
        except requests.exceptions.RequestException as e:
            await send_error_to_webhook(f"Error fetching value for wallet {wallet_id} on attempt {attempt + 1}: {e}")
            print(f"Error fetching value for wallet {wallet_id}: {e}")

        # Exponential backoff with random jitter
        wait_time = 2 ** attempt + random.uniform(0, 1)
        print(f"Retrying in {wait_time:.2f} seconds...")
        await asyncio.sleep(wait_time)

    await send_error_to_webhook(f"Failed to fetch value for wallet {wallet_id} after {retries} attempts.")
    return None


async def get_divi_price(retries=3):
    for attempt in range(retries):
        try:
            response = requests.get(DIVI_PRICE_URL, timeout=10)
            response.raise_for_status()
            return Decimal(response.text)
        except requests.exceptions.Timeout:
            await send_error_to_webhook(f"Timeout error on attempt {attempt + 1} for fetching Divi price.")
        except requests.exceptions.RequestException as e:
            await send_error_to_webhook(f"Error fetching Divi price on attempt {attempt + 1}: {e}")
            print(f"Error fetching Divi price: {e}")

        # Exponential backoff with random jitter
        wait_time = 2 ** attempt + random.uniform(0, 1)
        print(f"Retrying in {wait_time:.2f} seconds...")
        await asyncio.sleep(wait_time)

    await send_error_to_webhook(f"Failed to fetch Divi price after {retries} attempts.")
    return None


async def get_wallet_rank(wallet_id, retries=3):
    for attempt in range(retries):
        try:
            response = requests.get(
                f'https://chainz.cryptoid.info/divi/api.dws?q=richrank&a={wallet_id}&key={CRYPTOID_API_KEY}',
                timeout=10
            )
            response.raise_for_status()
            return response.text.strip()
        except requests.exceptions.Timeout:
            await send_error_to_webhook(
                f"Timeout error on attempt {attempt + 1} for fetching rank for wallet {wallet_id}.")
        except requests.exceptions.RequestException as e:
            await send_error_to_webhook(
                f"Error fetching rich rank for wallet {wallet_id} on attempt {attempt + 1}: {e}")
            print(f"Error fetching rich rank for wallet {wallet_id}: {e}")

        # Exponential backoff with random jitter
        wait_time = 2 ** attempt + random.uniform(0, 1)
        print(f"Retrying in {wait_time:.2f} seconds...")
        await asyncio.sleep(wait_time)

    await send_error_to_webhook(f"Failed to fetch rank for wallet {wallet_id} after {retries} attempts.")
    return "Unknown"



# Generate a wallet summary for a user
async def generate_wallet_summary(user_id):
    try:
        wallets = wallets_collection.find({"user_id": user_id})
        wallet_count = wallets_collection.count_documents({"user_id": user_id})
        if wallet_count == 0:
            return "🚫 You don't have any wallets added yet. Add a wallet using `!addwallet <wallet_address>`."
        wallet_summaries = []
        divi_price = await get_divi_price()
        for wallet in wallets:
            wallet_address = wallet['wallet_address']
            current_balance = wallet.get('current_balance', 0.0)
            rank = await get_wallet_rank(wallet_address)
            wallet_summary = (
                f"💼 **Wallet**: `{wallet_address}`\n"
                f"💰 **Balance**: {current_balance} DIVI\n"
                f"🏅 **Rich List Rank**: {rank}\n"
            )
            wallet_summaries.append(wallet_summary)
        divi_price_msg = f"🔖 **Divi Price**: ${divi_price:.4f} USD\n\n"
        final_summary = divi_price_msg + "\n".join(wallet_summaries)
        return final_summary
    except Exception as e:
        await send_error_to_webhook(f"Error generating wallet summary for user {user_id}: {e}")
        return "Error generating wallet summary."

async def display_help(message_channel):
    help_message = (
        "🆘 **Help Menu** 🆘\n"
        "Here are the commands you can use:\n"
        "`!addwallet <wallet_address>` - Add a new wallet to your watchlist (max 3 wallets).\n"
        "`!deletewallet <wallet_address>` - Remove a wallet from your watchlist.\n"
        "`!listwallets` - List all your added wallets and their balances.\n"
        "`!summary` - Get a detailed summary of your wallet(s).\n"
        "If you encounter an error, please check the commands and try again!"
    )
    await message_channel.send(help_message)

async def notify_discord_user(user_id, wallet_id, balance_difference):
    """Notify the user via Discord."""
    user = await client.fetch_user(user_id)
    balance_difference_float = float(balance_difference)
    if user:
        if balance_difference == 581.0:
            message = f"🎉 **Congratulations {user.mention}!** Wallet {wallet_id} just earned a staking reward of **{balance_difference}**! Keep it up! 🚀"
        else:
            message = f"📢 **Wallet Balance Change** for Wallet `{wallet_id}`!\nBalance changed by: {balance_difference_float}"
        await user.send(message)

async def monitor_wallets():
    while True:
        try:
            wallets = wallets_collection.find()
            for wallet in wallets:
                wallet_id = wallet['wallet_address']
                user_id = wallet['user_id']
                current_balance = Decimal(wallet.get('current_balance', 0.0))
                new_balance = await get_wallet_value(wallet_id)
                if new_balance is not None:
                    balance_difference = float(new_balance) - float(current_balance)
                    if balance_difference != 0:
                        await notify_discord_user(user_id, wallet_id, balance_difference)
                        wallets_collection.update_one(
                            {"wallet_address": wallet_id},
                            {"$set": {
                                "previous_balance": float(current_balance),
                                "current_balance": float(new_balance)
                            }}
                        )
        except Exception as e:
            await send_error_to_webhook(f"Error during wallet monitoring: {e}")
        await asyncio.sleep(60)

@client.event
async def on_ready():
    print(f'Bot is ready and logged in as {client.user}')


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        if message.content.startswith('!addwallet'):
            await send_webhook_log(message.author, f"!addwallet used for {message.author}")
            try:
                _, wallet_address = message.content.split(' ')
                response_message = await add_wallet(message.author.id, wallet_address)
                await message.channel.send(response_message)
            except Exception as e:
                await message.channel.send(f"Error adding wallet: {str(e)}")

        elif message.content.startswith('!deletewallet'):
            await send_webhook_log(message.author, f"!delete used for {message.author}")
            try:
                _, wallet_address = message.content.split(' ')
                await remove_wallet(message.author.id, wallet_address)
                await message.channel.send(f"Wallet {wallet_address} has been removed from your watchlist!")
            except Exception as e:
                await message.channel.send(f"Error deleting wallet: {str(e)}")

        elif message.content.startswith('!listwallets'):
            await send_webhook_log(message.author, f"!listwallet used for {message.author}")
            try:
                wallets = await list_wallets_by_user(message.author.id)
                if wallets:
                    wallet_list = '\n'.join(
                        [
                            f"💰 Wallet: {wallet['wallet_address']}\n   🔄 Current Balance: **{wallet['current_balance']}**\n"
                            for wallet in wallets
                        ]
                    )
                    await message.channel.send(
                        f"✨ Here are your wallets, my savvy investor:\n\n{wallet_list}\n\nKeep those coins shining! 🌟")
                else:
                    await message.channel.send(
                        "🚫 Oops! It looks like you don't have any wallets added yet. Add one using !addwallet <your_wallet_address> and start your journey to fortune! 💸")
            except Exception as e:
                await message.channel.send(f"Error listing wallets: {str(e)}")

        elif message.content.startswith('!help'):
            await send_webhook_log(message.author, f"!help used for {message.author}")
            await display_help(message.channel)

        elif message.content.startswith('!summary'):
            await send_webhook_log(message.author, f"!summary used for {message.author}")
            user_summary = await generate_wallet_summary(message.author.id)
            await message.channel.send(user_summary)

        elif message.content.startswith('!adminstats') and message.author.id == ADMIN_USER_ID:
            await send_admin_stats(message.channel)

        else:
            await message.channel.send("Error: Invalid command. Please use !help for instructions.")


async def add_wallet(user_id, wallet_address):
    """Add a wallet to the MongoDB collection and fetch the initial balance."""
    wallet_count = wallets_collection.count_documents({"user_id": user_id})

    if wallet_count >= 3:
        print(f"User {user_id} already has 3 wallets. Cannot add more.")
        return "You can only have a maximum of 3 wallets added."

    # Fetch the current wallet balance from the API
    new_balance = await get_wallet_value(wallet_address)
    if new_balance is None:
        return f"Error: Could not fetch the balance for wallet `{wallet_address}`."

    # Add the wallet to MongoDB with the actual balance
    wallets_collection.update_one(
        {"user_id": user_id, "wallet_address": wallet_address},
        {"$set": {
            "previous_balance": float(new_balance),  # Set previous balance to the same initially
            "current_balance": float(new_balance)    # Set current balance from the API
        }},
        upsert=True
    )

    print(f"Wallet added: {user_id}, {wallet_address} with balance {new_balance}")
    return f"Wallet `{wallet_address}` has been added to your watchlist with a balance of **{new_balance}**!"


async def remove_wallet(user_id, wallet_address):
    result = wallets_collection.delete_one({"user_id": user_id, "wallet_address": wallet_address})
    if result.deleted_count > 0:
        print(f"Wallet removed: {user_id}, {wallet_address}")
    else:
        print(f"Wallet not found: {user_id}, {wallet_address}")

async def list_wallets_by_user(user_id):
    wallets = wallets_collection.find({"user_id": user_id})
    return [{"wallet_address": wallet['wallet_address'], "current_balance": wallet['current_balance']} for wallet in wallets]


async def send_admin_stats(message_channel):
    """Send admin statistics about bot activity and performance."""
    total_wallets = wallets_collection.count_documents({})
    total_users = len(wallets_collection.distinct("user_id"))

    admin_message = (
        f"📊 **Admin Stats** 📊\n"
        f"Total Wallets: **{total_wallets}**\n"
        f"Total Users: **{total_users}**\n"
    )
    await message_channel.send(admin_message)


@client.event
async def on_connect():
    asyncio.create_task(monitor_wallets())


# Start the Discord bot
client.run(DISCORD_TOKEN)
