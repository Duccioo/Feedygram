#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram.ext import Updater, MessageHandler, Filters
from telegram import MessageEntity

import export_to_telegraph
from html_telegraph_poster import TelegraphPoster
import yaml
from telegram_util import matchKey, log_on_fail, log, tryDelete, autoDestroy, getBasicLog
import plain_db
from bs4 import BeautifulSoup
import album_sender

with open('token') as f:
    tele = Updater(f.read().strip(), use_context=True)


# info_log = tele.bot.get_chat(-1001436325054)

no_auth_link_users = [-1001399998441] # prevent token leak through @web_record

no_source_link = plain_db.loadKeyOnlyDB('no_source_link')
remove_origin = plain_db.loadKeyOnlyDB('remove_origin')

with open('telegraph_tokens') as f:
	telegraph_tokens = {}
	for k, v in yaml.load(f, Loader=yaml.FullLoader).items():
		telegraph_tokens[int(k)] = v

def saveTelegraphTokens():
	with open('telegraph_tokens', 'w') as f:
		f.write(yaml.dump(telegraph_tokens, sort_keys=True, indent=2))

def getSource(msg):
	if msg.from_user:
		return msg.from_user.id, msg.from_user.first_name, msg.from_user.username
	return msg.chat_id, msg.chat.title, msg.chat.username

def msgAuthUrl(msg, p):
	r = p.get_account_info(fields=['auth_url'])
	msg.reply_text('Use this url to login in 5 minutes: ' + r['auth_url'])

def msgTelegraphToken(msg):
	source_id, shortname, longname = getSource(msg)
	if source_id in telegraph_tokens:
		p = TelegraphPoster(access_token = telegraph_tokens[source_id])
	else:
		p = TelegraphPoster()
		r = p.create_api_token(shortname, longname)
		telegraph_tokens[source_id] = r['access_token']
		saveTelegraphTokens()
	if source_id not in no_auth_link_users:
		msgAuthUrl(msg, p)


def getAlbum(msg, url):
	if msg.text.endswith(' f') or msg.text.endswith(' full') or msg.text.endswith(' l'):
		return export_to_telegraph.getAlbum(url, word_limit=1000, paragraph_limit=20, append_source=True, append_url=False)
	if msg.text.endswith(' b') or msg.text.endswith(' brief'):
		return export_to_telegraph.getAlbum(url, append_source=True, append_url=False)

def getTelegraph(msg, url):
	source_id, _, _ = getSource(msg)
	if source_id not in telegraph_tokens:
		msgTelegraphToken(msg)
	export_to_telegraph.token = telegraph_tokens[source_id]
	return export_to_telegraph.export(url, throw_exception = True, 
		force = True, toSimplified = (
			'bot_simplify' in msg.text or msg.text.endswith(' s')),
		noAutoConvert = msg.text.endswith(' t') or msg.text.endswith(' noAutoConvert'),
		noSourceLink = str(msg.chat_id) in no_source_link._db.items)

def exportImp(msg):
	soup = BeautifulSoup(msg.text_html_urled, 'html.parser')
	for item in soup.find_all('a'):
		if 'http' in item.get('href'):
			url = item.get('href')
			album = getAlbum(msg, url)
			if album:
				album_sender.send_v2(msg.chat, album)
				continue
			result = getTelegraph(msg, url)
			yield result
			if str(msg.chat_id) in no_source_link._db.items:
				msg.chat.send_message(result)
			else:
				msg.chat.send_message('%s | [source](%s)' % (result, url), 
					parse_mode='Markdown')


def export(update, context):
	if update.edited_message or update.edited_channel_post:
		return
	msg = update.effective_message
	if msg.chat_id < 0 and 'source</a>' in msg.text_html_urled:
		return
	try:
		tmp_msg_1 = msg.chat.send_message('received')
	except:
		return
	error = ''
	result = []
	try:
		result = list(exportImp(msg))
		if str(msg.chat.id) in remove_origin._db.items:
			tryDelete(msg)
	except Exception as e:
		try:
			tmp_msg_2 = msg.chat.send_message(str(e)) 
			autoDestroy(tmp_msg_2, 0.05)
		except:
			... # In flood case, this would fail also
		error = ' error: ' + str(e)
	finally:
		# log_message = getBasicLog(msg) + error + ' result: ' + ' '.join(result)
		# try:
		# 	info_log.send_message(log_message, parse_mode='html', disable_web_page_preview=True)
		# except:
		# 	info_log.send_message(log_message, disable_web_page_preview=True)
		tmp_msg_1.delete()

with open('help.md') as f:
	help_message = f.read()

def toggleSourceLink(msg):
	result = no_source_link.toggle(msg.chat_id)
	if result:
		msg.reply_text('Source Link Off')
	else:
		msg.reply_text('Source Link On')

def toggleRemoveOrigin(msg):
	result = remove_origin.toggle(msg.chat_id)
	if result:
		msg.reply_text('Remove Original message On')
	else:
		msg.reply_text('Remove Original message Off')


def command(update, context):
	msg = update.message or update.channel_post
	if matchKey(msg.text, ['auth', 'token']):
		return msgTelegraphToken(msg)
	if matchKey(msg.text, ['source', 'tnsl', 'toggle_no_source_link']):
		return toggleSourceLink(msg)
	if matchKey(msg.text, ['origin', 'trmo', 'toggle_remove_origin']):
		return toggleRemoveOrigin(msg)
	if msg.chat_id > 0:
		msg.reply_text(help_message)

tele.dispatcher.add_handler(MessageHandler(Filters.text & 
	(Filters.entity('url') | Filters.entity(MessageEntity.TEXT_LINK)), export))
tele.dispatcher.add_handler(MessageHandler(Filters.command, command))

tele.start_polling()
tele.idle()