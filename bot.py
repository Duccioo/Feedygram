
import feedparser
import export_to_telegraph
import webpage2telegraph
from html_telegraph_poster import TelegraphPoster
from bs4 import BeautifulSoup
import album_sender


def getSource(msg):
	if msg.from_user:
		return msg.from_user.id, msg.from_user.first_name, msg.from_user.username
	return msg.chat_id, msg.chat.title, msg.chat.username

def msgAuthUrl(msg, p):
	r = p.get_account_info(fields=['auth_url'])
	msg.reply_text('Use this url to login in 5 minutes: ' + r['auth_url'])

def getAlbum(msg, url):
	if msg.text.endswith(' f') or msg.text.endswith(' full') or msg.text.endswith(' l'):
		return export_to_telegraph.getAlbum(url, word_limit=1000, paragraph_limit=20, append_source=True, append_url=False)
	if msg.text.endswith(' b') or msg.text.endswith(' brief'):
		return export_to_telegraph.getAlbum(url, append_source=True, append_url=False)

def getTelegraph(msg, url):
	
	return export_to_telegraph.export(url, throw_exception = True, 
		force = True, toSimplified = (
			'bot_simplify' in msg.text or msg.text.endswith(' s')),
		noAutoConvert = msg.text.endswith(' t') or msg.text.endswith(' noAutoConvert'))
		

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
			
			try:
				msg.chat.send_message('%s | [source](%s)' % (result, url), parse_mode='Markdown')
			except Exception as e:
    			 print(e)




Feed = feedparser.parse('https://multiplayer.it/feed/rss/homepage/')
pointer = Feed.entries[0]
print( "tutti", Feed.entries)
telegraph_url_f = webpage2telegraph.transfer(pointer.link)

telegraph_url_n = export_to_telegraph.export(pointer.link)
print (pointer.title)
print (pointer.link)
print ("telegraph funzia", telegraph_url_f)
print ("telegraph none", telegraph_url_n)