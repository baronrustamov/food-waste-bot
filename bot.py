import logging
import telegram
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          ConversationHandler)
from googlemaps import Client as GoogleMaps
import os
import json

tgt = json.load(open('./keys.json'))["tgt"]
chati = json.load(open('./keys.json'))["chati"]
gmaps = json.load(open('./keys.json'))["gmaps"]

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

LOCATION, PHOTO, DIET, SERVINGS, TIME, CONFIRMATION = range(6)

reply_keyboard = [['Confirm', 'Restart']]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
TOKEN = tgt
bot = telegram.Bot(token=TOKEN)
chat_id = chati
GMAPSAPI = gmaps
gmaps = GoogleMaps(GMAPSAPI)

PORT = int(os.environ.get('PORT', 5000))

def facts_to_str(user_data):
    facts = list()

    for key, value in user_data.items():
        facts.append('{} - {}'.format(key, value))

    return "\n".join(facts).join(['\n', '\n'])


def start(update, context):
    update.message.reply_text(
        "Привет! Я помогу вам избавиться от остатков пищи и предоставить ее тем, кому она действительно необходима с целью сократить пищевые отходы."
        "Чтобы начать, пожалуйста введить адрес, где можно забрать оставшуюся еду.")
    return LOCATION


def location(update, context):
    user = update.message.from_user
    user_data = context.user_data
    category = 'Location'
    text = update.message.text
    user_data[category] = text
    logger.info("Location of %s: %s", user.first_name, update.message.text)

    update.message.reply_text('Спасибо! Пожалуйста, отправьте фотографию остатков пищи,'
                              'чтобы пользователи знали, как выглядит еда или отправьте /skip, если вы не хотите.')
    return PHOTO


def photo(update, context):
    user = update.message.from_user
    user_data = context.user_data
    photo_file = update.message.photo[-1].get_file()
    photo_file.download('user_photo.jpg')
    category = 'Photo Provided'
    user_data[category] = 'Yes'
    logger.info("Photo of %s: %s", user.first_name, 'user_photo.jpg')
    update.message.reply_text('Отлично! Это вегетарианская пища? Пожалуйста, поделитесь диетическими характеристиками пищи.')

    return DIET


def skip_photo(update, context):
    user = update.message.from_user
    user_data = context.user_data
    category = 'Photo Provided'
    user_data[category] = 'No'
    logger.info("User %s did not send a photo.", user.first_name)
    update.message.reply_text('Отлично! Это вегетарианская пища? Пожалуйста, поделитесь диетическими характеристиками пищи.')

    return DIET


def diet(update, context):
    user = update.message.from_user
    user_data = context.user_data
    category = 'Dietary Specifications'
    text = update.message.text
    user_data[category] = text
    logger.info("Диетическая характеристика пищи: %s", update.message.text)
    update.message.reply_text('Какое количество порций?')

    return SERVINGS

def servings(update, context):
    user = update.message.from_user
    user_data = context.user_data
    category = 'Number of Servings'
    text = update.message.text
    user_data[category] = text
    logger.info("Количество порций: %s", update.message.text)
    update.message.reply_text('В какое время можно будет забрать еду?')

    return TIME
    
def time(update, context):
	user = update.message.from_user
	user_data = context.user_data
	category = 'Time to Take Food By'
	text = update.message.text
	user_data[category] = text
	logger.info("В какое время доступно: %s", update.message.text)
	update.message.reply_text("Спасибо за предоставление информации! Пожалуйста проверьте, всё ли правильно:"
								"{}".format(facts_to_str(user_data)), reply_markup=markup)

	return CONFIRMATION

def confirmation(update, context):
    user_data = context.user_data
    user = update.message.from_user
    update.message.reply_text("Спасибо! Я поделюсь Вашей информацией в канале @" + chat_id + "  сейчас.", reply_markup=ReplyKeyboardRemove())
    if (user_data['Photo Provided'] == 'Yes'):
        del user_data['Photo Provided']
        bot.send_photo(chat_id=chat_id, photo=open('user_photo.jpg', 'rb'), 
		caption="<b>Есть доступная еда!</b> Подробности ниже: \n {}".format(facts_to_str(user_data)) +
		"\n За дополнительной информацией обратитесь к поставщику {}".format(user.name), parse_mode=telegram.ParseMode.HTML)
    else:
        del user_data['Photo Provided']
        bot.sendMessage(chat_id=chat_id, 
            text="<b>Есть доступная еда!</b> Подробности ниже: \n {}".format(facts_to_str(user_data)) +
        "\n За дополнительной информацией обратитесь к поставщику {}".format(user.name), parse_mode=telegram.ParseMode.HTML)
    geocode_result = gmaps.geocode(user_data['Location'])
    lat = geocode_result[0]['geometry']['location'] ['lat']
    lng = geocode_result[0]['geometry']['location']['lng']
    bot.send_location(chat_id=chat_id, latitude=lat, longitude=lng)

    return ConversationHandler.END

def cancel(update, context):
    user = update.message.from_user
    logger.info("Пользователь %s отменил публикацию.", user.first_name)
    update.message.reply_text('До свидания! Буду ждать Вас в следущий раз.',
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler with the states LOCATION, PHOTO, DIET, SERVINGS, TIME, CONFIRMATION
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={

            LOCATION: [CommandHandler('start', start), MessageHandler(Filters.text, location)],

            PHOTO: [CommandHandler('start', start), MessageHandler(Filters.photo, photo),
                    CommandHandler('skip', skip_photo)],

            DIET: [CommandHandler('start', start), MessageHandler(Filters.text, diet)],

            SERVINGS: [CommandHandler('start', start), MessageHandler(Filters.text, servings)],

            TIME: [CommandHandler('start', start), MessageHandler(Filters.text, time)],

            CONFIRMATION: [MessageHandler(Filters.regex('^Confirm$'),
                                      confirmation),
            MessageHandler(Filters.regex('^Restart$'),
                                      start)
                       ]

        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conv_handler)

    # log all errors
    dp.add_error_handler(error)

    #updater.start_webhook(listen="0.0.0.0", port=int(PORT), url_path=TOKEN)
    #updater.bot.setWebhook('https://YOURHEROKUAPPNAME.herokuapp.com/' + TOKEN)

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
