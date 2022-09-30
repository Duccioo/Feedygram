# FeedRssTelegram

Bot Per creare Feed Personalizzati di Telegram che restituisce articoli in telegraph

ha bisogno di 1 sola variabile d'ambiente
TELEGRAM*TOKEN = \_your telegram token*

## cosedafare

Canale feed rss
funzionalità:

- [x] Poter aggiungere per ogni utente una personale lista di feed
- [x] controllo dopo un tot di minuti se sono arrivati nuovi feed
- [x] visualizzare tutti i link con un'apertura rapida
- [ ] aggiungere un campo per poter settare dove inviare i messaggi

prototipo docker-compose:

```python

        version: "2.1"
        services:
        feedergraph:
            image: duccioo/feedergraph:raspberrypi
            container_name: duccio-bot-portfolio
            environment:
            - TELEGRAM_TOKEN=*your telegram token* 
            - UPDATE_INTERVAL=*refresh rate* 

            restart: unless-stopped
```
