
<img src="https://res.cloudinary.com/duccio-me/image/upload/c_scale,r_300000,w_200/v1664798817/Tavolasaasdsegno_1_qzgmun.png" width=200 height=200 align="right">

# 🐕Feedygram

A simple *🤖Telegram Bot🤖* to keep track of your **RSS Feeds!**

*This bot was based on [RobotRSS by hamitdurmus](https://github.com/hamitdurmus/robotrss).*

Since I had to rewrite much of the code because the repo was no longer updated, 
I decided to create a new repo and while I was there I added various new features such 
as support for receiving **Telegraph links**

## Features

- **RSS Auto-Discovery:** Simply send any website homepage URL (e.g. `https://theverge.com` or `https://ansa.it`), and Feedygram automatically detects and links the RSS/Atom feed
- **Curated Feeds Catalog (`/explore`):** One-click subscriptions to top popular feeds across Tech, News, Gaming, and Science
- **Social & Media Resolvers:** Track YouTube (`/youtube @channel`), Reddit (`/reddit r/tech`), and Twitter/X (`/x @username`) natively
- **Modular Feed Provider Architecture:** Connect to local RSS feeds or external feed engines like [Lion Reader](https://github.com/brendanlong/lion-reader) and custom REST APIs
- **Keyword Filters:** Include (`+keyword`) and exclude (`-keyword`) specific topics per feed with `/filter`
- **OPML Import / Export:** Backup and restore all subscriptions with `/export` and `/import`
- **Channel & Group Broadcasting:** Forward news directly to Telegram channels and groups (`/channel`)
- **Instant TL;DR Summaries:** Ultra-lightweight extractive AI summaries with a single click on `📝 TL;DR`
- **Convert URL to support instant view (Telegraph)**
- **SQLite implementation** with foreign-key cascade integrity


## Run Locally

Clone the project

```bash
  git clone https://github.com/Duccioo/Feedygram
```

Go to the project directory

```bash
  cd Feedygram
```

Install dependencies

```bash
  pip install -r requirements.txt
```


Start the bot

**Watch out! Before start the bot set the environment variables ([see which](https://github.com/Duccioo/Feedygram/#Environment-Variables))**


```bash
  python ./src/bot.py
```


## Environment Variables

To run this project, add the following environment variables to your `.env` file:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `TELEGRAM_TOKEN` | Your Telegram bot token from [BotFather](https://t.me/BotFather) | *Required* |
| `UPDATE_INTERVAL` | Polling interval in seconds | `300` |
| `FEED_PROVIDER` | Feed backend provider (`local`, `lion_reader`, `rest`) | `local` |
| `FEED_API_URL` | Base URL for external API backend (e.g. `http://localhost:3000`) | `http://localhost:3000` |
| `FEED_API_KEY` | *(Optional)* Bearer token or API key for external backend | `None` |
| `TWITTER_RSS_BRIDGE` | *(Optional)* Custom template or base URL for X/Twitter RSS bridge | `https://nitter.net/{username}/rss` |


## Docker

You can pull Feedygram from DockerHub with :

```bash
docker pull duccioo/feedergraph
```

If you have a RaspberryPi then:

```bash
docker pull duccioo/feedergraph:raspberrypi
```


And for run it I recommend to use docker-compose:

```
version: "3"
services:
  feedergraph:
    image: duccioo/feedergraph:raspberrypi
    container_name: feedergraph
    volumes:
      - *path_for_persistent_database*:/app/src/database/data

    environment:
      - TELEGRAM_TOKEN=*your_telegram_bot_token*
      - UPDATE_INTERVAL=*time_before_update_feed example:( 300 )* 

    restart: unless-stopped

```
## Demo

Check out a live demo here: [@feedygram_BOT](http://t.me/feedygram_bot)
## Roadmap

- Twitter implementation

- A list of default website to subscribe

- Send message to a Telegram Channel



## Feedback

If you have any feedback, please reach out to me at meconcelliduccio@gmail.com or visit my website 
[duccio.me](https://duccio.me )

