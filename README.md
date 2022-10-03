
<img src="https://res.cloudinary.com/duccio-me/image/upload/c_scale,r_300000,w_200/v1664798817/Tavolasaasdsegno_1_qzgmun.png" width=200 height=200 align="right">

# 🐕Feedygram

A simple *🤖Telegram Bot🤖* to keep track of your **RSS Feeds!**

*This bot was based on [RobotRSS by hamitdurmus](https://github.com/hamitdurmus/robotrss).*

Since I had to rewrite much of the code because the repo was no longer updated, 
I decided to create a new repo and while I was there I added various new features such 
as support for receiving **Telegraph links**

## Features

- Easy to use
- Save your favorite RSS url
- Get **instant** feed from saved url
- **Convert URL to support instant view (Telegraph)**
- SQLite implementation
- Automatically assign a name to the url
- Support to run with RaspberryPi


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

To run this project, you will need to add the following environment variables to your *.env* file

`TELEGRAM_TOKEN` --> Your Telegram bot token from [BotFather](https://t.me/BotFather)

`UPDATE_INTERVAL` --> How much time must pass before updating the feed (in seconds)


## Docker

You can pull Feedygram from DockerHub with :

```
docker push duccioo/feedergraph
```

If you have a RaspberryPi then:

```
docker push duccioo/feedergraph:raspberrypi
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

