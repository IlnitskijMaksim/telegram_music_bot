import os, re, pymongo

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext, \
    CallbackQueryHandler

CHOOSING, SEARCHING_TRACK, SEARCHING_ALBUM, SEARCHING_BY_GENRE = range(4)
SPOTIPY_CLIENT_ID = 'afc788c5c37047d88323def34a3e55a7'
SPOTIPY_CLIENT_SECRET = 'b3a88d4426c141f992ffe036fefe8ef6'
SPOTIPY_REDIRECT_URI = 'https://telegram-music-bot-spotify-9e7cddf91b33.herokuapp.com/'

TELEGRAM_TOKEN = '6460071034:AAF-ZCJlgxTijiPesQFu0OJzDlH6u3rr_P4'

per_page = 5


def initialize_mongodb():
    client = pymongo.MongoClient("mongodb+srv://Immrtldrgn:zZzDrgnzZz123@cluster0.kgzirzk.mongodb.net/")
    db = client["TgBot"]
    users_collection = db["users"]
    tracks_collection = db["favorite_tracks"]
    return users_collection, tracks_collection


users_collection, tracks_collection = initialize_mongodb()


def search_spotify_tracks(query):
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET,
                                                   redirect_uri=SPOTIPY_REDIRECT_URI, scope="user-library-read"))
    results = sp.search(q=query, type='track')
    tracks = results['tracks']['items']
    return tracks


def search_spotify_albums(query):
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET,
                                                   redirect_uri=SPOTIPY_REDIRECT_URI, scope="user-library-read"))
    results = sp.search(q=query, type='album')
    albums = results['albums']['items']
    return albums


def search_spotify_genres(query):
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET,
                                                   redirect_uri=SPOTIPY_REDIRECT_URI, scope="user-library-read"))
    results = sp.search(q=f'genre:"{query}"', type='artist', limit=10)

    artists = results['artists']['items']
    return artists


def start(update: Update, context: CallbackContext):
    reply_keyboard = [['Пошук пісень'], ['Пошук альбомів'], ['Пошук за жанром'], ['Улюблене']]
    update.message.reply_text(
        "Привіт! Я бот для пошуку музики на Spotify. Щоб почати пошук нажміть на потрібну вам кнопку.",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )

    user_id = update.effective_user.id
    existing_user = users_collection.find_one({"user_id": user_id})

    if not existing_user:
        username = update.effective_user.username
        first_name = update.effective_user.first_name

        users_collection.insert_one({
            "user_id": user_id,
            "username": username,
            "first_name": first_name
        })

    return CHOOSING


def choose_action(update: Update, context: CallbackContext):
    user = update.message.from_user
    if update.message.text == 'Пошук пісень':
        update.message.reply_text(
            "Прекрасо! Тепер напишіть назву пісні або гурту, яку ви хочете знайти."
        )
        return SEARCHING_TRACK
    elif update.message.text == 'Пошук альбомів':
        update.message.reply_text(
            "Прекрасо! Тепер напишіть назву альбому або гурту, який ви хочете знайти."
        )
        return SEARCHING_ALBUM
    elif update.message.text == 'Пошук за жанром':
        update.message.reply_text(
            "Прекрасо! Тепер напишіть назву жанру, щоб знайти виконавців."
        )
        return SEARCHING_BY_GENRE


current_selection = {}


def search_track(update: Update, context: CallbackContext):
    query = update.message.text
    tracks = search_spotify_tracks(query)
    context.user_data['current_state'] = SEARCHING_TRACK

    if not tracks:
        update.message.reply_text("Пісні не знайдено.")
        return SEARCHING_TRACK

    user_id = update.effective_user.id
    context.user_data['type'] = 'track'
    context.user_data['items'] = tracks
    context.user_data['current_page'] = 0

    text, reply_markup = create_track_keyboard(context, user_id, page=0)

    if reply_markup:
        update.message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(reply_markup))
    else:
        update.message.reply_text(text)

    return SEARCHING_TRACK


def create_track_keyboard(context, user_id, page):
    tracks = context.user_data['items']
    per_page = 5

    total_results = len(tracks)
    total_pages = (total_results + per_page - 1) // per_page

    start = page * per_page
    end = (page + 1) * per_page
    tracks_to_display = tracks[start:end]

    reply_markup = []

    for idx, track in enumerate(tracks_to_display):
        track_name = track['name']
        artists = ', '.join([artist['name'] for artist in track['artists']])
        callback_data = f"track_{start + idx}"
        reply_markup.append([InlineKeyboardButton(f"{track_name} від {artists}", callback_data=callback_data)])

    total_pages = (len(tracks) + per_page - 1) // per_page

    if total_pages > 1:
        if end < len(tracks):
            reply_markup.append([InlineKeyboardButton("Наступна сторінка", callback_data=f"next_page_{page + 1}")])
        if page > 0:
            reply_markup.append([InlineKeyboardButton("Попередня сторінка", callback_data=f"prev_page_{page - 1}")])
    reply_markup.append([InlineKeyboardButton("Головне меню", callback_data="main_menu")])

    text = f"Ось що вдалось знайти:({page + 1}/{total_pages}):"

    return text, reply_markup


def create_album_keyboard(context, user_id, page):
    albums = context.user_data['items']

    start = page * per_page
    end = (page + 1) * per_page
    albums_to_display = albums[start:end]

    reply_markup = []

    for idx, album in enumerate(albums_to_display):
        album_name = album['name']
        artists = ', '.join([artist['name'] for artist in album['artists']])
        callback_data = f"album_{start + idx}"
        reply_markup.append([InlineKeyboardButton(f"{album_name} від {artists}", callback_data=callback_data)])

    total_pages = (len(albums) + per_page - 1) // per_page

    if total_pages > 1:
        if end < len(albums):
            reply_markup.append([InlineKeyboardButton("Наступна сторінка", callback_data=f"next_page_{page + 1}")])
        if page > 0:
            reply_markup.append([InlineKeyboardButton("Попередня сторінка", callback_data=f"prev_page_{page - 1}")])
    reply_markup.append([InlineKeyboardButton("Головне меню", callback_data="main_menu")])

    text = f"Ось що вдалося знайти ({page + 1}/{total_pages}):"

    return text, reply_markup


def search_album(update: Update, context: CallbackContext):
    query = update.message.text
    albums = search_spotify_albums(query)
    context.user_data['current_state'] = SEARCHING_ALBUM

    if not albums:
        update.message.reply_text("Альбоми не знайдено.")
        return SEARCHING_ALBUM

    user_id = update.effective_user.id
    context.user_data['type'] = 'album'
    context.user_data['items'] = albums  # Store all matching albums
    context.user_data['current_page'] = 0  # Initialize the current page

    text, reply_markup = create_album_keyboard(context, user_id, page=0)

    if reply_markup:
        update.message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(reply_markup))
    else:
        update.message.reply_text(text)  # No inline keyboard

    return SEARCHING_ALBUM


def create_artist_keyboard(context, user_id, page):
    artists = context.user_data['items']
    per_page = 5

    start = page * per_page
    end = (page + 1) * per_page
    artists_to_display = artists[start:end]

    reply_markup = []

    for idx, artist in enumerate(artists_to_display):
        artist_name = artist['name']
        callback_data = f"artist_{start + idx}"
        reply_markup.append([InlineKeyboardButton(f"{artist_name}", callback_data=callback_data)])

    total_pages = (len(artists) + per_page - 1) // per_page

    if total_pages > 1:
        if end < len(artists):
            reply_markup.append([InlineKeyboardButton("Next", callback_data=f"next_page_{page + 1}")])
        if page > 0:
            reply_markup.append([InlineKeyboardButton("Previous", callback_data=f"prev_page_{page - 1}")])
    reply_markup.append([InlineKeyboardButton("Головне меню", callback_data='main_menu')])

    text = f"Ось що вдалося знайти ({page + 1}/{total_pages}):"

    return text, reply_markup


def search_by_genre(update: Update, context: CallbackContext):
    query = update.message.text
    artists = search_spotify_genres(query)
    context.user_data['current_state'] = SEARCHING_BY_GENRE

    if not artists:
        update.message.reply_text("Виконавців за обраним жанром не знайдено.")
        return SEARCHING_BY_GENRE

    user_id = update.effective_user.id
    context.user_data['type'] = 'artist'
    context.user_data['items'] = artists
    context.user_data['current_page'] = 0

    text, reply_markup = create_artist_keyboard(context, user_id, page=0)

    if reply_markup:
        update.message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(reply_markup))
    else:
        update.message.reply_text(text)

    return SEARCHING_BY_GENRE


def show_selected_item(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    current_selection = context.user_data

    if 'items' not in current_selection:
        return

    items = current_selection['items']

    try:
        selected_index = int(query.data.split('_')[1])
        selected_item = items[selected_index]

        # Store the selected item's data in user_data
        context.user_data['selected_item'] = selected_item

        track_name = selected_item['name']
        artists = ', '.join([artist['name'] for artist in selected_item['artists']])
        external_url = selected_item['external_urls']['spotify']

        # Create an InlineKeyboardMarkup with the "Добавить в улюбленное" button
        keyboard = [
            [InlineKeyboardButton("Назад", callback_data="back_to_list"),
             InlineKeyboardButton("Добавить в улюбленное", callback_data="add_to_favorite")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        context.user_data['current_state'] = SEARCHING_TRACK
        query.edit_message_text(text=f"Песня: {track_name}\nИсполнитель: {artists}\nСлушать на Spotify: {external_url}",
                                reply_markup=reply_markup)

    except (IndexError, ValueError):
        query.answer("Ошибка: Неправильный формат запроса.")


def add_to_favorite(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    selected_item = context.user_data.get('selected_item')

    if selected_item:
        track_name = selected_item['name']
        artist_name = ', '.join([artist['name'] for artist in selected_item['artists']])
        spotify_url = selected_item['external_urls']['spotify']

        # Проверяем, есть ли песня уже в избранном
        existing_track = tracks_collection.find_one({
            "user_id": user_id,
            "track_name": track_name,
            "artist_name": artist_name
        })

        if existing_track:
            query.answer("Пісня вже додана до вашого списку улюблених.")
        else:
            # Песня не найдена в избранном, добавляем её
            song_details = {
                "user_id": user_id,
                "track_name": track_name,
                "artist_name": artist_name,
                "spotify_url": spotify_url
            }
            add_to_favorite_db(song_details)
            query.answer("Пісня додана до вашого списку улюблених.")
    else:
        query.answer("Помилка: Пісня не вибрана.")

    # Return to the list of songs
    show_selected_item(update, context)


def add_to_favorite_db(song_details):
    tracks_collection.insert_one(song_details)


def show_selected_album(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    current_selection = context.user_data

    if 'items' not in current_selection:
        return

    items = current_selection['items']
    selected_index = int(query.data.split('_')[1])
    selected_album = items[selected_index]

    album_name = selected_album['name']
    artists = ', '.join([artist['name'] for artist in selected_album['artists']])
    external_url = selected_album['external_urls']['spotify']
    text = f"Альбом: {album_name}\nВиконавець: {artists}\nСлухати на Spotify: {external_url}"

    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="back_to_list")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.user_data['current_state'] = SEARCHING_ALBUM
    query.edit_message_text(text=text, reply_markup=reply_markup)


def show_selected_artist(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    current_selection = context.user_data

    if 'items' not in current_selection:
        return

    items = current_selection['items']
    selected_index = int(query.data.split('_')[1])
    selected_artist = items[selected_index]

    artist_name = selected_artist['name']
    external_url = selected_artist['external_urls']['spotify']
    text = f"Виконавець: {artist_name}\nСлухати на Spotify: {external_url}"

    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="back_to_list")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.user_data['current_state'] = SEARCHING_BY_GENRE
    query.edit_message_text(text=text, reply_markup=reply_markup)


def show_favorites(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    favorite_tracks = tracks_collection.find({"user_id": user_id})
    favorite_tracks_count = tracks_collection.count_documents({"user_id": user_id})
    if favorite_tracks_count == 0:
        update.message.reply_text("У вас поки що немає улюблених пісень.")
        return

    response_text = "Ваші улюблені пісні:\n"
    for track in favorite_tracks:
        response_text += f"{track['track_name']} від {track['artist_name']}\n"

    update.message.reply_text(response_text)


def handle_navigation(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    current_state = context.user_data.get('current_state', CHOOSING)

    if query.data == "main_menu":
        text = "Ви повернулись у головне меню. Оберіть іншу дію"
        query.edit_message_text(text)

        reply_markup = ReplyKeyboardMarkup(
            [['Пошук пісень'], ['Пошук альбомів'], ['Пошук за жанром'], ['Улюблені пісні']], one_time_keyboard=True)
        return CHOOSING

    # Check if query.data starts with "next_page" or "prev_page"
    if query.data.startswith("next_page_"):
        page = int(query.data.split("_")[2])  # Extract the page number
    elif query.data.startswith("prev_page_"):
        page = int(query.data.split("_")[2])  # Extract the page number
    else:
        page = 0  # Default to 0 if not recognized

    context.user_data['current_page'] = page

    if current_state == SEARCHING_TRACK:
        text, reply_markup = create_track_keyboard(context, user_id, page)
    elif current_state == SEARCHING_ALBUM:
        text, reply_markup = create_album_keyboard(context, user_id, page)
    elif current_state == SEARCHING_BY_GENRE:
        text, reply_markup = create_artist_keyboard(context, user_id, page)
    else:
        return CHOOSING

    if reply_markup:
        query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(reply_markup))
    else:
        query.edit_message_text(text)

    return current_state


def back_to_list(update: Update, context: CallbackContext):
    query = update.callback_query

    if 'back_to_list' in query.data:
        current_state = context.user_data.get('current_state', None)

        if current_state == SEARCHING_TRACK:
            text, reply_markup = create_track_keyboard(context, update.effective_user.id, page=0)
            query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(reply_markup))
            return SEARCHING_TRACK

        elif current_state == SEARCHING_ALBUM:
            text, reply_markup = create_album_keyboard(context, update.effective_user.id, page=0)
            query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(reply_markup))
            return SEARCHING_ALBUM

        elif current_state == SEARCHING_BY_GENRE:
            text, reply_markup = create_artist_keyboard(context, update.effective_user.id, page=0)
            query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(reply_markup))
            return SEARCHING_BY_GENRE

    return CHOOSING


def serialize_inline_keyboard(reply_markup):
    if isinstance(reply_markup, InlineKeyboardMarkup):
        serialized_reply_markup = []
        for row in reply_markup.inline_keyboard:
            serialized_row = []
            for button in row:
                serialized_button = {
                    'text': button.text,
                    'callback_data': button.callback_data,
                }
                serialized_row.append(serialized_button)
            serialized_reply_markup.append(serialized_row)
        return InlineKeyboardMarkup(serialized_reply_markup)
    return None


def main():
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING: [
                MessageHandler(Filters.regex('^Пошук пісень$'), choose_action),
                MessageHandler(Filters.regex('^Пошук альбомів$'), choose_action),
                MessageHandler(Filters.regex('^Пошук за жанром$'), choose_action),
                MessageHandler(Filters.regex('^Улюблене$'), show_favorites),
                CallbackQueryHandler(handle_navigation, pattern="back_to_list"),
            ],
            SEARCHING_TRACK: [
                MessageHandler(Filters.text & ~Filters.command, search_track),
                CallbackQueryHandler(handle_navigation, pattern="next_page"),
                CallbackQueryHandler(handle_navigation, pattern="prev_page"),
                CallbackQueryHandler(handle_navigation, pattern="main_menu"),
            ],
            SEARCHING_ALBUM: [
                MessageHandler(Filters.text & ~Filters.command, search_album),
                CallbackQueryHandler(handle_navigation, pattern="main_menu"),
                CallbackQueryHandler(handle_navigation, pattern="next_page"),
                CallbackQueryHandler(handle_navigation, pattern="prev_page"),
            ],
            SEARCHING_BY_GENRE: [
                MessageHandler(Filters.text & ~Filters.command, search_by_genre),
                CallbackQueryHandler(handle_navigation, pattern="main_menu"),
            ],
        },
        fallbacks=[],
    )

    dispatcher.add_handler(CallbackQueryHandler(show_selected_artist, pattern=r"^artist_\d+$"))
    dispatcher.add_handler(CallbackQueryHandler(show_selected_album, pattern=r"^album_\d+$"))
    dispatcher.add_handler(CallbackQueryHandler(show_selected_item, pattern=r"^track_\d+$"))
    dispatcher.add_handler(CallbackQueryHandler(add_to_favorite, pattern="add_to_favorite"))
    dispatcher.add_handler(CallbackQueryHandler(back_to_list, pattern="back_to_list"))
    dispatcher.add_handler(CallbackQueryHandler(handle_navigation, pattern="prev_page"))
    dispatcher.add_handler(CallbackQueryHandler(handle_navigation, pattern="next_page"))
    dispatcher.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
