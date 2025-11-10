import discord
from discord.ext import commands
import asyncio
from asyncio import run_coroutine_threadsafe
from urllib import parse, request
import re
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
from yt_dlp import YoutubeDL
import socket

class musicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.is_playing = {}
        self.is_paused = {}
        self.music_queue = {}
        self.queueIndex = {}

        self.YTDL_OPTIONS = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'extractaudio': True,
            'audioformat': 'mp3',
            'restrictfilenames': True,
            'logtostderr': False,
            'ignoreerrors': False,
            'default_search': 'ytsearch',
            'source_address': '0.0.0.0',
            'age_limit': 99,
            'skip_download': True,
            'cookiefile': None,  # Can add cookie file path if needed
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.FFmpeg_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -loglevel warning',
            'options': '-vn'
        }

        self.embedBlue = 0x2c76dd
        self.embedRed = 0xdf1141
        self.embedGreen = 0x0eaa51
        self.vc = {}

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            id = int(guild.id)
            self.is_playing[id] = False
            self.is_paused[id] = False
            self.music_queue[id] = []
            self.queueIndex[id] = 0
            self.vc[id] = None

    def now_playing_embed(self, ctx, song):
        title = song['title']
        link = song['link']
        thumbnail = song['thumbnail']
        author = ctx.author
        avatar = author.avatar.url if author.avatar else author.default_avatar.url

        embed = discord.Embed(
            title="ဖွင့်လိုက်ပြီ မေလိုး",
            description=f'[{title}]({link})',
            color=self.embedBlue
        )
        embed.set_thumbnail(url=thumbnail)
        embed.set_footer(text=f'အဲ့မေလိုးဖွင့်တာ: {str(author)}', icon_url=avatar)
        return embed

    async def join_vc(self, ctx, channel):
        id = int(ctx.guild.id)
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                print(f"Attempting to join channel: {channel.name} (Attempt {attempt + 1}/{max_retries})")
                
                # If we already have a connection, disconnect first to clean up
                if self.vc[id] is not None:
                    if self.vc[id].is_connected():
                        if self.vc[id].channel == channel:
                            print(f"Already connected to {channel.name}")
                            return
                        else:
                            print(f"Moving from {self.vc[id].channel.name} to {channel.name}")
                            await self.vc[id].move_to(channel)
                            print(f"Moved to {channel.name}")
                            return
                    else:
                        # Clean up disconnected voice client
                        self.vc[id] = None
                
                # Create new connection
                self.vc[id] = await channel.connect(timeout=10.0, reconnect=True)
                print(f"Connected to {channel.name}")
                return
                    
            except discord.ClientException as e:
                print(f"Discord client error (attempt {attempt + 1}): {e}")
                if "already connected" in str(e).lower():
                    print("Already connected, continuing...")
                    return
                self.vc[id] = None
                
            except Exception as e:
                print(f"Error joining voice channel (attempt {attempt + 1}): {e}")
                print(f"Error type: {type(e)}")
                self.vc[id] = None
                
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
        
        # If all retries failed
        await ctx.send("Failed to connect to voice channel after multiple attempts. Please check your network connection.")
        raise Exception("Failed to connect to voice channel after retries")

    def is_youtube_url(self, url):
        """Check if the provided string is a YouTube URL and return video ID"""
        youtube_patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
            r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
            r'(?:https?://)?(?:www\.)?m\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in youtube_patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)  # Return the video ID
        return None

    def search_YT(self, search):
        query = parse.urlencode({'search_query': search})
        html_content = request.urlopen('http://www.youtube.com/results?' + query)
        search_results = re.findall(r'/watch\?v=(.{11})', html_content.read().decode())
        return search_results[:10]

    def extract_YT(self, url):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with YoutubeDL(self.YTDL_OPTIONS) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    # Get the best audio format, avoiding HLS streams
                    audio_url = None
                    if 'formats' in info:
                        # Look for audio-only formats first, avoiding HLS
                        audio_formats = [f for f in info['formats'] 
                                       if f.get('acodec') != 'none' 
                                       and f.get('vcodec') == 'none'
                                       and f.get('protocol') not in ['m3u8_native', 'hls']
                                       and f.get('url')]
                        if audio_formats:
                            # Sort by quality preference
                            audio_formats.sort(key=lambda x: x.get('abr', 0), reverse=True)
                            audio_url = audio_formats[0]['url']
                        else:
                            # Fall back to any format with audio, avoiding HLS
                            formats_with_audio = [f for f in info['formats'] 
                                                if f.get('acodec') != 'none' 
                                                and f.get('protocol') not in ['m3u8_native', 'hls']
                                                and f.get('url')]
                            if formats_with_audio:
                                formats_with_audio.sort(key=lambda x: x.get('abr', 0), reverse=True)
                                audio_url = formats_with_audio[0]['url']
                    
                    if not audio_url:
                        print(f"No suitable audio stream found (attempt {attempt + 1})")
                        if attempt < max_retries - 1:
                            import time
                            time.sleep(1)
                            continue
                        return False
                    
                    # Test if URL is accessible
                    try:
                        import urllib.request
                        urllib.request.urlopen(audio_url, timeout=5)
                    except:
                        print(f"Audio URL not accessible (attempt {attempt + 1})")
                        if attempt < max_retries - 1:
                            import time
                            time.sleep(1)
                            continue
                        return False
                    
                    return {
                        'link': 'https://www.youtube.com/watch?v=' + url,
                        'thumbnail': f'https://i.ytimg.com/vi/{url}/hqdefault.jpg',
                        'source': audio_url,
                        'title': info.get('title', 'Unknown Title'),
                        'duration': info.get('duration', 0)
                    }
                    
            except Exception as e:
                print(f"Error extracting video info (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2)
                    continue
                return False
        
        return False

    async def play_next(self, ctx):
        id = int(ctx.guild.id)

        if self.queueIndex[id] + 1 < len(self.music_queue[id]):
            self.queueIndex[id] += 1
            song = self.music_queue[id][self.queueIndex[id]][0]
            message = self.now_playing_embed(ctx, song)
            # Send message without blocking - use asyncio.create_task to avoid blocking
            asyncio.create_task(ctx.send(embed=message))

            def after_playback(error):
                if error:
                    print(f"Player error: {error}")
                asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)

            try:
                audio_source = discord.FFmpegPCMAudio(song['source'], **self.FFmpeg_OPTIONS)
                self.vc[id].play(audio_source, after=after_playback)
                self.is_playing[id] = True
            except Exception as e:
                print(f"Error playing next audio: {e}")
                # Since we're already in an async function, just call play_next directly
                try:
                    await self.play_next(ctx)
                except:
                    pass
        else:
            self.is_playing[id] = False
            self.queueIndex[id] = 0
            self.music_queue[id] = []  # Clear the queue when done
            # Don't disconnect - stay in voice channel

    async def play_music(self, ctx):
        id = int(ctx.guild.id)

        if self.queueIndex[id] < len(self.music_queue[id]):
            self.is_playing[id] = True
            self.is_paused[id] = False

            try:
                # Check if we're connected to voice, if not, try to connect
                if self.vc[id] is None or not self.vc[id].is_connected():
                    print(f"Not connected to voice, attempting to join...")
                    channel = self.music_queue[id][self.queueIndex[id]][1]
                    print(f"Target channel: {channel.name}")
                    await self.join_vc(ctx, channel)
                    # Give a moment for the connection to stabilize
                    await asyncio.sleep(0.5)
                
                song = self.music_queue[id][self.queueIndex[id]][0]
                message = self.now_playing_embed(ctx, song)
                await ctx.send(embed=message)

                def after_playback(error):
                    if error:
                        print(f"Player error: {error}")
                    asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)

                print(f"Attempting to play: {song['title']}")
                
                # Check if we have a voice client and it's connected
                if self.vc[id] is None:
                    await ctx.send("Failed to connect to voice channel - no voice client.")
                    self.is_playing[id] = False
                    return
                
                if not self.vc[id].is_connected():
                    await ctx.send("Failed to connect to voice channel - not connected.")
                    self.is_playing[id] = False
                    return
                
                audio_source = discord.FFmpegPCMAudio(song['source'], **self.FFmpeg_OPTIONS)
                self.vc[id].play(audio_source, after=after_playback)
                print("Audio playback started successfully")
            except Exception as e:
                print(f"Error in play_music: {e}")
                await ctx.send(f"Error playing music: {e}")
                self.is_playing[id] = False
                return
        else:
            await ctx.send("No more songs in the queue.")
            self.is_playing[id] = False
            self.queueIndex[id] = 0

    @commands.command(name='ဝင်', aliases=['j'],help = "")
    async def ဝင်(self, ctx):
        if ctx.author.voice:
            user_channel = ctx.author.voice.channel
            print(f"User is in channel: {user_channel.name}")
            
            # Check bot permissions
            permissions = user_channel.permissions_for(ctx.guild.me)
            print(f"Bot permissions - Connect: {permissions.connect}, Speak: {permissions.speak}")
            
            if not permissions.connect:
                await ctx.send("I don't have permission to connect to voice channels.")
                return
            if not permissions.speak:
                await ctx.send("I don't have permission to speak in voice channels.")
                return
                
            await self.join_vc(ctx, user_channel)
            await ctx.send(f"Joined {user_channel} voice channel.")
        else:
            await ctx.send("You are not connected to a voice channel.")

    @commands.command(name='ထွက်', aliases=['l'], help="")
    async def ထွက်(self, ctx):
        id = int(ctx.guild.id)
        self.is_playing[id] = False
        self.is_paused[id] = False
        self.music_queue[id] = []
        self.queueIndex[id] = 0

        if self.vc[id] is not None:
            await ctx.send(f"Left {self.vc[id].channel} voice channel.")
            await self.vc[id].disconnect()
            self.vc[id] = None
    @commands.command(name='ဖွင့်', aliases=['p','phwint'],help = "")
    async def ဖွင့်(self, ctx, *args):
        search = " ".join(args)
        id = int(ctx.guild.id)
        try: 
            userChannel = ctx.author.voice.channel
        except AttributeError:
            await ctx.send("You are not connected to a voice channel.")
            return
        if not args:
            if len(self.music_queue[id]) == 0:
                await ctx.send("No songs in the queue.")
                return
            elif not self.is_playing[id]:
                if len(self.music_queue[id]) == 0 or self.vc[id] is None:
                    await self.play_music(ctx)
                else:
                    self.is_paused[id] = False
                    self.is_playing[id] = True
                    self.vc[id].resume()
            else:
                return
        else:
            # Check if it's a YouTube URL first
            video_id = self.is_youtube_url(search)
            if video_id:
                print(f"Direct YouTube URL detected. Video ID: {video_id}")
                song = self.extract_YT(video_id)
            else:
                print(f"Searching YouTube for: {search}")
                search_results = self.search_YT(search)
                if not search_results:
                    await ctx.send("No search results found.")
                    return
                song = self.extract_YT(search_results[0])
            
            if type(song) == type(True):
                await ctx.send("No results found or error extracting audio.")
                return
            else:
                print(f"Song extracted: {song['title']}")
                print(f"Audio source URL: {song['source'][:100]}...")  
                self.music_queue[id].append((song, userChannel))
                
                if not self.is_playing[id]:
                    await self.play_music(ctx)
                else:
                    embed = discord.Embed(
                        title="စောင့်ဦး မေလိုး",
                        description=f'[{song["title"]}]({song["link"]})',
                        color=self.embedGreen
                    )
                    embed.set_thumbnail(url=song["thumbnail"])
                    author = ctx.author
                    avatar = author.avatar.url if author.avatar else author.default_avatar.url
                    embed.set_footer(text=f'အဲ့မေလိုးဖွင့်တာ: {str(author)}', icon_url=avatar)
                    await ctx.send(embed=embed)


       
