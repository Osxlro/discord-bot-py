import discord
import wavelink
import datetime
from config import settings
from services.core import lang_service, persistence_service

def format_duration(milliseconds: int) -> str:
    """Formatea milisegundos a MM:SS o HH:MM:SS."""
    seconds = milliseconds // 1000
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}:{minutes:02}:{seconds:02}"
    return f"{minutes}:{seconds:02}"

def get_source_icon(track: wavelink.Playable) -> str:
    """Retorna el emoji correspondiente a la fuente de la canción."""
    source = getattr(track, 'source', '').lower()
    uri = (track.uri or "").lower()
    
    if "youtube" in source or "youtube" in uri or "youtu.be" in uri:
        return settings.MUSIC_CONFIG["SOURCE_EMOJIS"]["youtube"]
    if "spotify" in source or "spotify" in uri:
        return settings.MUSIC_CONFIG["SOURCE_EMOJIS"]["spotify"]
    if "soundcloud" in source or "soundcloud" in uri:
        return settings.MUSIC_CONFIG["SOURCE_EMOJIS"]["soundcloud"]
    return settings.MUSIC_CONFIG["SOURCE_EMOJIS"]["unknown"]

def get_source_color(track: wavelink.Playable) -> int:
    """Retorna el color hexadecimal de la marca de la fuente."""
    uri = (track.uri or "").lower()
    if "spotify" in uri: return 0x1DB954
    if "youtube" in uri or "youtu.be" in uri: return 0xFF0000
    if "soundcloud" in uri: return 0xFF5500
    return settings.COLORS["INFO"]

def create_np_embed(player: wavelink.Player, track: wavelink.Playable, lang: str) -> discord.Embed:
    """Genera el embed de 'Reproduciendo Ahora' con barra de progreso."""
    position = player.position
    length = track.length
    
    if track.is_stream:
        pos_str = lang_service.get_text("music_live", lang)
        len_str = "∞"
        bar_len = settings.MUSIC_CONFIG["STREAM_BAR_LENGTH"]
        bar = settings.MUSIC_CONFIG["PROGRESS_BAR_CHAR"] * bar_len + settings.MUSIC_CONFIG["PROGRESS_BAR_POINTER"]
    else:
        total_blocks = settings.MUSIC_CONFIG["PROGRESS_BAR_LENGTH"]
        progress = int((position / length) * total_blocks) if length > 0 else 0
        progress = min(progress, total_blocks) 
        bar = settings.MUSIC_CONFIG["PROGRESS_BAR_CHAR"] * progress + settings.MUSIC_CONFIG["PROGRESS_BAR_POINTER"] + settings.MUSIC_CONFIG["PROGRESS_BAR_CHAR"] * (total_blocks - progress)
        pos_str = format_duration(position)
        len_str = format_duration(length)

    icon = get_source_icon(track)
    desc = lang_service.get_text("music_np_desc", lang, title=track.title, uri=track.uri or "", pos=pos_str, bar=bar, len=len_str)

    embed = discord.Embed(
        title=f"{icon} {lang_service.get_text('music_now_playing_title', lang)}",
        description=desc,
        color=get_source_color(track)
    )
    if track.artwork: embed.set_thumbnail(url=track.artwork)
    
    if hasattr(track, "requester") and track.requester:
        embed.set_footer(text=lang_service.get_text("music_requested_by", lang, user=track.requester.display_name), icon_url=track.requester.display_avatar.url)
        
    fields = [
        (lang_service.get_text("music_field_author", lang), track.author, True),
        (lang_service.get_text("music_field_album", lang), getattr(getattr(track, "album", None), "name", None), True),
        (lang_service.get_text("music_field_year", lang), getattr(track, "year", None), True)
    ]

    for name, value, inline in fields:
        if value:
            embed.add_field(name=name, value=str(value), inline=inline)

    return embed

class MusicControls(discord.ui.View):
    """Botones interactivos para controlar la música."""
    def __init__(self, player: wavelink.Player, author_id: int = None, lang: str = "es"):
        super().__init__(timeout=settings.MUSIC_CONFIG["CONTROLS_TIMEOUT"])
        self.player = player
        self.author_id = author_id
        self.lang = lang
        self.player.last_view = self 
        self._sync_state()

    def _sync_state(self):
        loop_map = {
            wavelink.QueueMode.loop: (settings.MUSIC_CONFIG["LOOP_EMOJIS"]["TRACK"], discord.ButtonStyle.success),
            wavelink.QueueMode.loop_all: (settings.MUSIC_CONFIG["LOOP_EMOJIS"]["QUEUE"], discord.ButtonStyle.success),
            wavelink.QueueMode.normal: (settings.MUSIC_CONFIG["LOOP_EMOJIS"]["OFF"], discord.ButtonStyle.secondary)
        }

        for child in self.children:
            if not isinstance(child, discord.ui.Button): continue
            
            if str(child.emoji) == settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["PAUSE_RESUME"]:
                child.style = discord.ButtonStyle.danger if self.player.paused else discord.ButtonStyle.primary
            
            elif str(child.emoji) == settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["AUTOPLAY"]:
                is_smart = getattr(self.player, "smart_autoplay", False)
                child.style = discord.ButtonStyle.success if is_smart else discord.ButtonStyle.secondary
            
            elif str(child.emoji) in settings.MUSIC_CONFIG["LOOP_EMOJIS"].values():
                emoji, style = loop_map.get(self.player.queue.mode, loop_map[wavelink.QueueMode.normal])
                child.emoji, child.style = emoji, style

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not self.player.connected:
             await interaction.response.send_message(lang_service.get_text("music_error_nothing", self.lang), ephemeral=True)
             return False

        if self.author_id and interaction.user.id != self.author_id:
            await interaction.response.send_message(lang_service.get_text("music_control_owner_error", self.lang), ephemeral=True)
            return False
        
        if not interaction.user.voice or (self.player.channel and interaction.user.voice.channel.id != self.player.channel.id):
             await interaction.response.send_message(lang_service.get_text("music_control_voice_error", self.lang), ephemeral=True)
             return False

        return True

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            if hasattr(self.player, "last_msg") and self.player.last_msg:
                await self.player.last_msg.edit(view=self)
        except discord.HTTPException:
            pass

    @discord.ui.button(emoji=settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["PREVIOUS"], style=discord.ButtonStyle.secondary, row=0)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.player.playing or not self.player.current:
             return await interaction.response.send_message(lang_service.get_text("music_error_nothing", self.lang), ephemeral=True)

        if self.player.position > 10000:
            await self.player.seek(0)
            msg = lang_service.get_text("music_restarted", self.lang)
        else:
            history = self.player.queue.history
            if len(history) == 0:
                await self.player.seek(0)
                msg = lang_service.get_text("music_restarted", self.lang)
            else:
                prev_track = history.pop()
                current_track = self.player.current
                self.player.queue.put_at(0, current_track)
                await self.player.play(prev_track)
                msg = lang_service.get_text("music_previous", self.lang)
        
        await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(emoji=settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["PAUSE_RESUME"], style=discord.ButtonStyle.primary, row=0)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_state = not self.player.paused
        await self.player.pause(new_state)
        button.style = discord.ButtonStyle.danger if new_state else discord.ButtonStyle.primary
        msg_key = "music_paused" if new_state else "music_resumed"
        try: await interaction.response.edit_message(view=self)
        except discord.HTTPException: pass
        await interaction.followup.send(lang_service.get_text(msg_key, self.lang), ephemeral=True)

    @discord.ui.button(emoji=settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["SKIP"], style=discord.ButtonStyle.secondary, row=0)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.player.playing or not self.player.current:
             return await interaction.response.send_message(lang_service.get_text("music_error_nothing", self.lang), ephemeral=True)

        await self.player.skip(force=True)
        msg = lang_service.get_text("music_skipped", self.lang)
        await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(emoji=settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["STOP"], style=discord.ButtonStyle.danger, row=0)
    async def stop_music(self, interaction: discord.Interaction, button: discord.ui.Button):
        from services.features import music_service
        for child in self.children:
            child.disabled = True
        self.stop()
        msg = lang_service.get_text("music_stopped", self.lang)
        try:
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(msg, ephemeral=True)
        except discord.HTTPException: pass

        await music_service.cleanup_player(self.player, skip_message_edit=True)
        await persistence_service.clear("music", self.player.guild.id)
        if self.player.connected: await self.player.disconnect()

    @discord.ui.button(emoji=settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["SHUFFLE"], style=discord.ButtonStyle.secondary, row=0)
    async def shuffle(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.player.queue.shuffle()
        msg = lang_service.get_text("music_shuffled", self.lang)
        await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(emoji=settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["QUEUE"], style=discord.ButtonStyle.secondary, row=1)
    async def show_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        from services.features import music_service
        if self.player.queue.is_empty:
            return await interaction.response.send_message(lang_service.get_text("music_queue_empty", self.lang), ephemeral=True)
        
        pages = music_service.get_queue_pages(self.player, self.lang)
        await interaction.response.send_message(embed=pages[0], ephemeral=True)

    @discord.ui.button(emoji=settings.MUSIC_CONFIG["LOOP_EMOJIS"]["OFF"], style=discord.ButtonStyle.secondary, row=1)
    async def loop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.player.queue.mode == wavelink.QueueMode.normal:
            self.player.queue.mode = wavelink.QueueMode.loop
            msg = lang_service.get_text("music_loop_track", self.lang)
        elif self.player.queue.mode == wavelink.QueueMode.loop:
            self.player.queue.mode = wavelink.QueueMode.loop_all
            msg = lang_service.get_text("music_loop_queue", self.lang)
        else:
            self.player.queue.mode = wavelink.QueueMode.normal
            msg = lang_service.get_text("music_loop_off", self.lang)
        
        self._sync_state()
        try:
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(msg, ephemeral=True)
        except discord.HTTPException: pass

    @discord.ui.button(emoji=settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["AUTOPLAY"], style=discord.ButtonStyle.secondary, row=1)
    async def autoplay(self, interaction: discord.Interaction, button: discord.ui.Button):
        current = getattr(self.player, "smart_autoplay", False)
        self.player.smart_autoplay = not current
        self.player.autoplay = wavelink.AutoPlayMode.disabled
        
        msg = lang_service.get_text("music_autoplay_on" if self.player.smart_autoplay else "music_autoplay_off", self.lang)
        self._sync_state()
        try:
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(msg, ephemeral=True)
        except discord.HTTPException: pass

    @discord.ui.button(emoji=settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["LYRICS"], style=discord.ButtonStyle.secondary, row=1)
    async def lyrics(self, interaction: discord.Interaction, button: discord.ui.Button):
        from services.integrations import lyrics_service
        if not self.player.current:
            return await interaction.response.send_message(lang_service.get_text("music_error_nothing", self.lang), ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        track = self.player.current
        res = await lyrics_service.get_lyrics(track.title, track.author)
        
        if not res:
            return await interaction.followup.send(lang_service.get_text("music_lyrics_not_found", self.lang), ephemeral=True)
        
        embed = discord.Embed(title=lang_service.get_text("music_lyrics_title", self.lang, title=track.title), 
                              description=res[:2000], color=settings.COLORS["INFO"])
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(emoji=settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["VOL_DOWN"], style=discord.ButtonStyle.secondary, row=2)
    async def vol_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        from services.features import music_service
        new_vol = max(self.player.volume - settings.MUSIC_CONFIG["VOLUME_STEP"], 0)
        await self.player.set_volume(new_vol)
        if self.player.current:
            await music_service.update_presence(interaction.client, self.player, self.player.current, self.lang)
        await interaction.response.send_message(lang_service.get_text("music_vol_changed", self.lang, vol=new_vol), ephemeral=True)

    @discord.ui.button(emoji=settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["VOL_UP"], style=discord.ButtonStyle.secondary, row=2)
    async def vol_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        from services.features import music_service
        new_vol = min(self.player.volume + settings.MUSIC_CONFIG["VOLUME_STEP"], 100)
        await self.player.set_volume(new_vol)
        if self.player.current:
            await music_service.update_presence(interaction.client, self.player, self.player.current, self.lang)
        await interaction.response.send_message(lang_service.get_text("music_vol_changed", self.lang, vol=new_vol), ephemeral=True)