import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Ваши данные от Spotify
SPOTIPY_CLIENT_ID = 'afc788c5c37047d88323def34a3e55a7'
SPOTIPY_CLIENT_SECRET = 'b3a88d4426c141f992ffe036fefe8ef6'
SPOTIPY_REDIRECT_URI = 'http://localhost:8888/callback'

# Ваш токен доступа от BotFather
TELEGRAM_TOKEN = '6460071034:AAF-ZCJlgxTijiPesQFu0OJzDlH6u3rr_P4'

# Функция для поиска трека на Spotify
def search_spotify_track(query):
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET, redirect_uri=SPOTIPY_REDIRECT_URI, scope="user-library-read"))
    results = sp.search(q=query, type='track')
    if results['tracks']['items']:
        track = results['tracks']['items'][0]
        return f"{track['name']} by {', '.join([artist['name'] for artist in track['artists']])} - {track['external_urls']['spotify']}"
    else:
        return "Трек не найден."

# Обработка команды /start
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Привет! Я бот для поиска музыки на Spotify. Просто отправь мне название трека или исполнителя.")

# Обработка текстовых сообщений с запросом музыки
def search_music(update: Update, context: CallbackContext):
    query = update.message.text
    result = search_spotify_track(query)
    update.message.reply_text(result)

def main():
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Обработчики команд
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, search_music))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
