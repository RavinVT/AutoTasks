import discord
from discord import app_commands
from discord.ext import tasks
import os
from dotenv import load_dotenv
import requests
from pathlib import Path
import yaml
from datetime import datetime
import feedparser
from TikTokApi import TikTokApi
import sys
import shutil
import subprocess
import importlib


def resource_path(relative_path: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative_path
    return Path(relative_path).absolute()

def copy_file_from_exe(filename: str, destination: Path | str) -> None:
    src = resource_path(filename)
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dest)
    print(f"[ AutoTasks ][ Copy ] Copied {src} -> {dest}")

def copy_folder_from_exe(foldername: str, destination: str):
    src = resource_path(foldername)
    shutil.copytree(src, destination, dirs_exist_ok=True)
    print(f"[ AutoTasks ][ Copy ] Copied folder {src} -> {destination}")


def ensure_package(package: str, install_name: str = None):
    """Try to import a package, and install it if missing."""
    if install_name is None:
        install_name = package
    try:
        importlib.import_module(package)
    except ImportError:
        print(f"Installing missing package: {install_name} ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", install_name])

def ensure_playwright_browsers():
    try:
        # Try importing playwright
        from playwright.sync_api import sync_playwright
        return True
    except Exception:
        pass

    print("Downloading Playwright browsers ...")
    try:
        subprocess.check_call([sys.executable, "-m", "playwright", "install"])
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "firefox"])
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "webkit"])
        subprocess.check_call(["playwright", "install"])
        subprocess.check_call(["playwright", "install", "chromium"])
        subprocess.check_call(["playwright", "install", "firefox"])
        subprocess.check_call(["playwright", "install", "webkit"])
        return True
    except Exception as e:
        print("Failed to install Playwright browsers:", e)
        return False


appdata = Path(os.getenv("APPDATA")) / "AutoTasks"
appdata.mkdir(parents=True, exist_ok=True)


appdata_env = Path(appdata / ".env")

ensure_package("playwright")
ensure_playwright_browsers()

browser_path = os.path.join(os.path.dirname(__file__), "ms-playwright")
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browser_path


if not (appdata.exists() and appdata_env.exists()):
    try:
        copy_file_from_exe(".env", appdata_env)
        copy_folder_from_exe("ms-playwright", "ms-playwright")
    except Exception as error:
        print(f"[ AutoTasks ][ Installer ] Failed to install: missing files, not all files could be found!\nError: {error}")
        sys.exit()


load_dotenv(appdata_env)


class LiveView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

        self.add_item(discord.ui.Button(label="Watch Stream", url=f"https://twitch.tv/{os.getenv('TWITCH_USER').lower()}"))

class YouTubeView(discord.ui.View):
    def __init__(self, video_url: str) -> None:
        super().__init__(timeout=None)

        self.add_item(discord.ui.Button(label="Watch Video", url=f"{video_url}"))


class StreamingAutoTasks(discord.AutoShardedClient):
    def __init__(self):
        super().__init__(
            intents=discord.Intents.all(),
            description="The auto health checkup tool"
        )
        self.was_live: bool = False
        self.latest_video_id: str = ""
        self.latest_tweet_id: int = 0
        self.latest_tiktok_id: str = ""
        self.times_checked_for_stream: int = 0
        self.times_found_active_stream: int = 0
        self.datapath: Path = Path(appdata / "data.yml")
        self.guild = None
        self.tree = app_commands.CommandTree(self)
    

    async def on_ready(self) -> None:
        await self.wait_until_ready()
        print(f"[ AutoTasks ] Logged in as: {self.user} ({self.user.id})")
        self.guild = self.get_guild(os.getenv("GUILD_ID"))

        twitch_enable = True if os.getenv("TWITCH_ENABLE").lower() == "true" else False
        youtube_enable = True if os.getenv("YOUTUBE_ENABLE").lower() == "true" else False
        twitter_enable = True if os.getenv("TWITTER_ENABLE").lower() == "true" else False
        tiktok_enable = True if os.getenv("TIKTOK_ENABLE").lower() == "true" else False

        print(f"[ AutoTasks ] Is Twitch Enabled? {'yes' if (twitch_enable) else 'no'}")
        print(f"[ AutoTasks ] Is YouTube Enabled? {'yes' if (youtube_enable) else 'no'}")
        print(f"[ AutoTasks ] Is Twitter Enabled? {'yes' if (twitter_enable) else 'no'}")
        print(f"[ AutoTasks ] Is TikTok Enabled? {'yes' if (tiktok_enable) else 'no'}")

        if twitch_enable:
            self.auto_twitch.start()
        if youtube_enable:
            self.auto_youtube.start()
        if twitter_enable:
            self.auto_twitter.start()
        if tiktok_enable:
            self.auto_tiktok.start()


    def get_twitch_token(self) -> str:
        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": os.getenv("CLIENT_ID"),
            "client_secret": os.getenv("CLIENT_SECRET"),
            "grant_type": "client_credentials"
        }
        r = requests.post(url, params=params).json()
        return r["access_token"]

    def is_live(self) -> tuple[bool, dict]:
        url = "https://api.twitch.tv/helix/streams"
        TWITCH_TOKEN = self.get_twitch_token()
        headers = {
            "Client-ID": os.getenv("CLIENT_ID"),
            "Authorization": f"Bearer {TWITCH_TOKEN}"
        }
        params = {"user_login": os.getenv("TWITCH_USER").lower()}
        r = requests.get(url, headers=headers, params=params).json()

        streams = r.get("data", [])
        if not streams:
            return False, {}

        stream = streams[0]

        # Extra sanity check
        if stream.get("user_name", "").lower() != os.getenv("TWITCH_USER").lower():
            return False, {}

        return True, stream


    def load(self) -> None:
        if self.datapath.exists():
            print("[ AutoTasks ] Loading \"data.yml\"")
            with self.datapath.open("r") as f:
                data = yaml.safe_load(f)
            self.times_checked_for_stream = data.get("streams-checked", 0)
            self.times_found_active_stream = data.get("streams-found", 0)
            self.latest_video_id = data.get("latest-video-id", "")
            self.latest_tweet_id = data.get("latest-tweet-id", 0)
            self.latest_tiktok_id = data.get("latest-tiktok-id", "0")
    
    def save(self) -> None:
        print("[ AutoTasks ] Saving \"data.yml\"")
        with self.datapath.open("w") as f:
            yaml.safe_dump({
                "streams-checked": self.times_checked_for_stream,
                "streams-found": self.times_found_active_stream,
                "latest-video-id": self.latest_video_id,
                "latest-tweet-id": self.latest_tweet_id,
                "latest-tiktok-id": self.latest_tiktok_id
            }, f)


    @tasks.loop(minutes=2, seconds=30)
    async def auto_twitch(self) -> None:
        print("[ AutoTasks ][ Twitch ] Checking for active stream!")
        self.times_checked_for_stream += 1
        channel = self.get_channel(int(os.getenv("CHANNEL_ID")))
        live, data = self.is_live()
        if live and not self.was_live:
            embed = discord.Embed(
                title=f"{os.getenv('TWITCH_USER')}'s live on Twitch!",
                description=f"### ***{data.get('title', '')}***\n\n#### {data.get('game_name', '')}",
                colour=discord.Colour.dark_purple(),
                timestamp=datetime.now()
            )
            await channel.send(content="@everyone", embed=embed, view=LiveView())
            self.was_live = True
            self.times_found_active_stream += 1
            print("[ AutoTasks ][ Twitch ] Found active stream!")
        elif not live and self.was_live:
            msg = await channel.send(f"{os.getenv('TWITCH_USER')} just went offline.")
            await msg.publish()
            self.was_live = False
            print("[ AutoTasks ][ Twitch ] Stream ended!")
        else:
            print("[ AutoTasks ][ Twitch ] No active stream found!")
    
    @tasks.loop(minutes=10)
    async def auto_youtube(self) -> None:
        print("[ AutoTasks ][ YouTube ] Checking for new video!")
        api_key = os.getenv("GOOGLE_API")
        channel_id = os.getenv("YOUTUBE_ID")

        search_url = (
            f"https://www.googleapis.com/youtube/v3/search"
            f"?key={api_key}&channelId={channel_id}&part=snippet,id&order=date&maxResults=1"
        )
        response = requests.get(search_url).json()

        if "items" not in response or not response["items"]:
            if response["error"]["code"] == 403 and response["error"]["errors"][0]["reason"] == "quotaExceeded":
                print("[ AutoTasks ][ YouTube ] You have exceeded your youtube quota, if you want more you can goto `https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas` to get more")
                return
            else:
                print("[ AutoTasks ][ YouTube ] API error:", response)
                return

        try:
            latest_video = response["items"][0]
            video_id = latest_video["id"]["videoId"]
            title = latest_video["snippet"]["title"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            video_url_api = (
                f"https://www.googleapis.com/youtube/v3/videos"
                f"?key={api_key}&id={video_id}&part=snippet"
            )
            video_response = requests.get(video_url_api).json()

            if "items" not in video_response or not video_response["items"]:
                print("[ AutoTasks ][ YouTube ] API error:", video_response)
                return

            description = video_response["items"][0]["snippet"]["description"]

            channel = self.get_channel(int(os.getenv("CHANNEL_ID")))
            if video_id and video_id != self.latest_video_id:
                self.latest_video_id = video_id
                embed = discord.Embed(
                    title=f"Video: {title}",
                    url=video_url,
                    description=description[:500] + "..." if len(description) > 500 else description
                )
                embed.set_author(name="New YouTube Video!")
                embed.set_thumbnail(url=video_response["items"][0]["snippet"]["thumbnails"]["high"]["url"])
                msg = await channel.send("@everyone", embed=embed, view=YouTubeView(video_url))
                await msg.publish()
                print("[ AutoTasks ][ YouTube ] Found new video!")
            else:
                print("[ AutoTasks ][ YouTube ] No new video found!")

        except Exception as e:
            print("YouTube task error:", e, response)

    @tasks.loop(minutes=2, seconds=30)
    async def auto_twitter(self) -> None:
        print("[ AutoTasks ][ Twitter ] Checking for new post!")
        feed_url = f"https://nitter.net/{os.getenv('TWITTER_USERNAME')}/rss"
        feed = feedparser.parse(feed_url)

        if not feed.entries:
            print("[ AutoTasks ][ Twitter ] No entires found yet, skipping!")
            return
        
        latest = feed.entries[0]
        tweet_id = latest.id
        tweet_url = latest.link
        tweet_text = latest.title

        channel = self.get_channel(int(os.getenv("CHANNEL_ID")))

        if tweet_id != self.latest_tweet_id:
            self.latest_tweet_id = tweet_id
            embed = discord.Embed(
                description=tweet_text,
                url=tweet_url,
                color=0x1DA1F2
            )
            embed.set_author(name="New Tweet!", icon_url="https://abs.twimg.com/icons/apple-touch-icon-192x192.png")
            embed.set_image(url=tweet_url.replace("twitter.com", "vxtwitter.com").replace("x.com", "vxtwitter.com"))
            msg = await channel.send("@everyone", embed=embed)
            await msg.publish()
            print("[ AutoTasks ][ Twitter ] Found new post!")
        else:
            print("[ AutoTasks ][ Twitter ] No new post found!")
    
    @tasks.loop(minutes=2, seconds=30)
    async def auto_tiktok(self) -> None:
        print("[ AutoTasks ][ TikTok ] Checking for new video!")
        try:
            username = os.getenv("TIKTOK_USERNAME").lower()
            channel = self.get_channel(int(os.getenv("CHANNEL_ID")))
            api = TikTokApi()
            await api.create_sessions(ms_tokens=[os.getenv("TIKTOK_SESSION")])
            user = api.user(username=username)

            try:
                videos = user.videos(count=1)
                latest = await anext(videos, None)
            except Exception as e:
                print("[ AutoTasks ][ TikTok ] Failed to fetch user/videos:", e)
                return

            if not latest:
                print("[ AutoTasks ][ TikTok ] No entries found, skipping!")
                return

            video_id = latest.id
            desc = latest.as_dict.get("desc", "(no description)")
            video_url = f"https://www.tiktok.com/@{user.username}/video/{video_id}"

            if video_id != self.latest_tiktok_id:
                self.latest_tiktok_id = video_id

                thumbnail_url = None
                if hasattr(latest, "video") and "cover" in latest.video:
                    thumbnail_url = latest.video["cover"]

                embed = discord.Embed(
                    title=f"New TikTok by @{user.username}",
                    url=video_url,
                    description=desc[:500] + "..." if len(desc) > 500 else desc,
                    color=0x69C9D0  # TikTok teal
                )
                if thumbnail_url:
                    embed.set_image(url=thumbnail_url)

                embed.set_author(
                    name="TikTok",
                    url=f"https://www.tiktok.com/@{user.username}",
                    icon_url="https://upload.wikimedia.org/wikipedia/en/thumb/a/a9/TikTok_logo.svg/1200px-TikTok_logo.svg.png"
                )

                msg = await channel.send("@everyone", embed=embed)
                await msg.publish()
                print("[ AutoTasks ][ TikTok ] New video found!")
            else:
                print("[ AutoTasks ][ TikTok ] No new video found!")
            await api.close_sessions()
        except:
            print("[ AutoTasks ][ TikTok ] Failed to install, attempting to install playwright")
            if not ensure_playwright_browsers():
                print("[ AutoTasks ][ TikTok ] Failed to install, properly! please intall manually!")
