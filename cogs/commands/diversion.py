import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
import asyncio
import logging
from services.features import diversion_service, trivia_service
from services.features.hangman_service import HangmanService, normalize_word
from services.core import lang_service, db_service
from services.utils import embed_service
from ui.trivia_ui import TriviaView
from ui.hangman_ui import HangmanConfigView, HangmanGameView, HANGMAN_PICS

logger = logging.getLogger(__name__)

class Diversion(commands.Cog):
    """
    Cog de entretenimiento y minijuegos.
    Contiene comandos para interactuar con emojis, azar, confesiones y juegos clásicos.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._active_hangman_channels = set()

    @commands.hybrid_command(name="jumbo", description="Muestra la imagen de un emoji en grande.")
    @app_commands.describe(emoji="Pon aquí el emoji personalizado")
    async def jumbo(self, ctx: commands.Context, emoji: str):
        """Amplía un emoji personalizado para ver su imagen en alta resolución."""
        # Obtener idioma del servidor o global
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        # Delegar el procesamiento del emoji al servicio
        embed, error = await diversion_service.handle_jumbo(emoji, lang)
        
        if error:
            # Responder con error si el emoji no es válido o no es personalizado
            return await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), error, lite=True), ephemeral=True)
        
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="coinflip", description="Lanza una moneda.")
    async def coinflip(self, ctx: commands.Context):
        """Simula el lanzamiento de una moneda (Cara o Cruz)."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        # Obtener el embed con el resultado y el GIF correspondiente desde el servicio
        embed = diversion_service.handle_coinflip(lang)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="choice", description="Elige entre dos opciones.")
    async def eleccion(self, ctx: commands.Context, opcion_a: str, opcion_b: str):
        """Ayuda al usuario a decidir entre dos opciones dadas."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        # El servicio elige una opción al azar y construye el embed
        embed = diversion_service.handle_choice(opcion_a, opcion_b, lang)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="emojimix", description="Mezcla dos emojis.")
    async def emojimix(self, ctx: commands.Context, emoji1: str, emoji2: str):
        """Combina dos emojis usando la API de Google Emoji Kitchen."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        # El servicio genera la URL de la imagen combinada
        embed = diversion_service.handle_emojimix(emoji1, emoji2, lang)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="confess", description="Confesión anónima.")
    @app_commands.describe(secreto="Tu secreto.")
    async def confesar(self, ctx: commands.Context, *, secreto: str):
        """Envía un mensaje anónimo a un canal de confesiones configurado."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        # El servicio verifica la configuración del servidor y prepara el embed anónimo
        channel_id, embed, error = await diversion_service.handle_confess(ctx.guild.id if ctx.guild else None, secreto, lang)
        
        if error:
            # Error si el canal no está configurado
            return await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), error, lite=True), ephemeral=True)
            
        # Obtener el objeto del canal de Discord
        canal = self.bot.get_channel(channel_id)
        if not canal: return

        try:
            # Enviar la confesión al canal destino
            await canal.send(embed=embed)
            # Confirmar al usuario de forma efímera
            msg = lang_service.get_text("confess_sent", lang, channel=canal.mention)
            await ctx.reply(embed=embed_service.success(lang_service.get_text("title_success", lang), msg, lite=True), ephemeral=True)
        except discord.Forbidden:
            # Error si el bot no tiene permisos de escritura en el canal de confesiones
            await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("confess_error_perms", lang), lite=True), ephemeral=True)

    @commands.hybrid_command(name="8ball", description="Pregúntale a la bola mágica.")
    @app_commands.describe(pregunta="Tu pregunta")
    async def eightball(self, ctx: commands.Context, pregunta: str):
        """Responde a una pregunta con una de las respuestas clásicas de la bola 8."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        # El servicio elige una respuesta aleatoria localizada
        embed = diversion_service.handle_8ball(pregunta, lang)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="trivia", description="Inicia una ronda de trivia de opción múltiple.")
    async def trivia(self, ctx: commands.Context):
        """Obtiene una pregunta de trivia aleatoria y presenta 4 opciones con botones."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        await ctx.defer()
        
        question_data = await trivia_service.fetch_trivia_question(lang)
        if not question_data:
            return await ctx.reply(embed=embed_service.error(
                lang_service.get_text("title_error", lang),
                lang_service.get_text("trivia_error_api", lang),
                lite=True
            ))
            
        # Generar el embed de la pregunta
        letter_emojis = ["🇦", "🇧", "🇨", "🇩"]
        options_text = ""
        for i, opt in enumerate(question_data["options"]):
            options_text += f"> {letter_emojis[i]} {opt}\n"
            
        title = lang_service.get_text("trivia_embed_title", lang)
        desc = (
            f"**{question_data['question']}**\n\n"
            f"{options_text}\n"
            f"> **📁 {lang_service.get_text('trivia_category', lang)}:** {question_data['category'].title()}\n"
            f"> **⚡ {lang_service.get_text('trivia_difficulty', lang)}:** {question_data['difficulty'].title()}"
        )
        
        embed = embed_service.fun(title, desc)
        
        # Crear la vista
        view = TriviaView(
            author=ctx.author,
            correct_index=question_data["correct_index"],
            options=question_data["options"],
            correct_answer=question_data["correct_answer"],
            difficulty=question_data["difficulty"],
            lang=lang
        )
        
        view.message = await ctx.reply(embed=embed, view=view)

    @commands.hybrid_command(name="anime", description="Muestra una imagen de anime aleatoria.")
    async def anime(self, ctx: commands.Context):
        """Muestra una imagen de anime aleatoria de NekosAPI."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        await ctx.defer()
        
        embed, error = await diversion_service.handle_anime(lang)
        if error:
            return await ctx.reply(embed=embed_service.error(
                lang_service.get_text("title_error", lang), error, lite=True
            ))
            
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="hangman", description="Juega al clásico juego del ahorcado.")
    async def hangman(self, ctx: commands.Context):
        """Inicia una partida de Ahorcado interactiva."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        # Evitar múltiples juegos en el mismo canal
        if ctx.channel.id in self._active_hangman_channels:
            return await ctx.reply("❌ Ya hay una partida de Ahorcado activa en este canal.", ephemeral=True)
            
        self._active_hangman_channels.add(ctx.channel.id)
        
        try:
            # 1. Configuración de partida
            config_view = HangmanConfigView(ctx.author, lang)
            embed = config_view.get_embed()
            config_view.message = await ctx.reply(embed=embed, view=config_view)
            
            await config_view.wait()
            
            if config_view.status != "start":
                self._active_hangman_channels.discard(ctx.channel.id)
                return
                
            # Eliminar mensaje de configuración para limpiar el canal
            try:
                await config_view.message.delete()
            except Exception:
                pass
                
            mode = config_view.mode
            difficulty = config_view.difficulty
            category = config_view.category
            
            # Obtener palabra inicial
            try:
                # Mostrar typing mientras se obtiene la palabra
                await ctx.channel.typing()
            except Exception:
                pass
                
            word_data = await HangmanService.get_word(difficulty, category, lang, ctx.guild.id if ctx.guild else None)
            if not word_data:
                self._active_hangman_channels.discard(ctx.channel.id)
                return await ctx.send(embed=embed_service.error(
                    lang_service.get_text("title_error", lang),
                    lang_service.get_text("hangman_error_fetch", lang),
                    lite=True
                ))
                
            # 2. Ejecutar juego
            if mode == "solo":
                await self._run_solo_game(ctx, word_data, lang)
            else:
                await self._run_multiplayer_game(ctx, word_data, lang, difficulty, category)
        finally:
            self._active_hangman_channels.discard(ctx.channel.id)

    async def _run_solo_game(self, ctx: commands.Context, word_data: dict, lang: str):
        word = word_data["word"]
        normalized_word = word_data["normalized_word"]
        hint = word_data["hint"]
        category = word_data["category"]
        
        lives = 6
        guessed_letters = set()
        guessed_word = ["_" if char.isalpha() else char for char in word]
        
        hint_revealed = False
        hint_letter = None
        
        def make_embed(lives: int, guessed_word: list, hint: str, category: str, guessed_letters: set, remaining: float, hint_letter: str = None) -> discord.Embed:
            title = lang_service.get_text("hangman_game_title", lang)
            pic = HANGMAN_PICS[6 - lives]
            word_display = " ".join([f"`{c}`" for c in guessed_word])
            guessed_display = ", ".join([f"`{c.upper()}`" for c in sorted(guessed_letters)]) if guessed_letters else "---"
            
            if remaining <= 60.0:
                hint_display = hint
            else:
                hint_display = lang_service.get_text("hangman_hint_hidden", lang)
                
            desc = (
                f"{pic}\n"
                f"📝 **{lang_service.get_text('hangman_game_word', lang)}**\n"
                f"> {word_display}\n\n"
                f"📋 **Información de la Partida**\n"
                f"> 📂 **{lang_service.get_text('hangman_game_category', lang)}:** {category.capitalize()}\n"
                f"> 💡 **{lang_service.get_text('hangman_game_hint', lang)}:** {hint_display}\n"
                f"> ❤️ **{lang_service.get_text('hangman_game_lives', lang)}:** {lives} / 6\n"
                f"> ⏱️ **Tiempo de Juego:** {max(0, int(remaining))}s restantes\n\n"
                f"🔠 **{lang_service.get_text('hangman_game_guesses', lang)}**\n"
                f"> {guessed_display}\n"
            )
            if hint_letter:
                pista_revelada_label = lang_service.get_text("hangman_hint_label", lang)
                desc = desc.replace("📋 Información de la Partida", f"💡 **{pista_revelada_label}:** `{hint_letter.upper()}`\n\n📋 Información de la Partida")
                
            desc += f"\n{lang_service.get_text('hangman_game_input_instruction', lang)}"
            return embed_service.fun(title, desc)
            
        game_view = HangmanGameView(ctx.author, lang, is_solo=True)
        game_view.active_task = asyncio.current_task()
        
        start_time = asyncio.get_event_loop().time()
        remaining = 180.0
        
        embed = make_embed(lives, guessed_word, hint, category, guessed_letters, remaining, None)
        msg = await ctx.send(embed=embed, view=game_view)
        
        def check(m):
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id and len(m.content.strip()) > 0
            
        try:
            while lives > 0 and "_" in guessed_word:
                elapsed = asyncio.get_event_loop().time() - start_time
                remaining = 180.0 - elapsed
                if remaining <= 0:
                    break
                    
                # Revelar pista al restar 1 minuto o menos
                if remaining <= 60.0 and not hint_revealed:
                    hint_revealed = True
                    hint_letter = HangmanService.get_initial_hint(normalized_word, guessed_letters)
                    if hint_letter:
                        guessed_letters.add(hint_letter)
                        for i, char in enumerate(normalized_word):
                            if char == hint_letter:
                                guessed_word[i] = word[i]
                        try:
                            hint_msg_text = lang_service.get_text("hangman_hint_revealed_chat", lang, letter=hint_letter.upper())
                            await ctx.send(hint_msg_text)
                        except Exception:
                            await ctx.send(f"💡 **Pista:** Se ha revelado la letra `{hint_letter.upper()}` al quedar menos de 1 minuto.")

                embed = make_embed(lives, guessed_word, hint, category, guessed_letters, remaining, hint_letter if hint_revealed else None)
                await msg.edit(embed=embed, view=game_view)
                
                timeout_val = min(remaining, 5.0)
                try:
                    guess_msg = await self.bot.wait_for('message', check=check, timeout=timeout_val)
                except asyncio.TimeoutError:
                    continue
                
                try:
                    await guess_msg.delete()
                except Exception:
                    pass
                    
                guess = guess_msg.content.strip().lower()
                guess_norm = normalize_word(guess)
                
                if not guess_norm.strip():
                    continue
                    
                if len(guess_norm) == 1:
                    if guess_norm in guessed_letters:
                        continue
                    guessed_letters.add(guess_norm)
                    
                    if guess_norm in normalized_word:
                        for i, char in enumerate(normalized_word):
                            if char == guess_norm:
                                guessed_word[i] = word[i]
                    else:
                        lives -= 1
                else:
                    if guess_norm == normalized_word:
                        guessed_word = list(word)
                    else:
                        lives -= 1
                        
            elapsed = asyncio.get_event_loop().time() - start_time
            remaining = 180.0 - elapsed
            if remaining <= 0 and "_" in guessed_word:
                embed = make_embed(lives, guessed_word, hint, category, guessed_letters, 0.0, hint_letter if hint_revealed else None)
                try:
                    await msg.edit(embed=embed, view=None)
                except Exception:
                    pass
                title = lang_service.get_text("hangman_timeout_title", lang)
                desc = lang_service.get_text("hangman_solo_lose_desc", lang, word=word, coins=0)
                await ctx.send(embed=embed_service.error(title, desc))
                return

        except asyncio.CancelledError:
            pass
            
        try:
            await msg.edit(view=None)
        except Exception:
            pass
            
        won = "_" not in guessed_word
        total_letters = len([c for c in word if c.isalpha()])
        revealed_letters = sum(1 for c in guessed_word if c != "_")
        guessed_ratio = (revealed_letters / total_letters) if total_letters > 0 else 0.0
        
        coins = HangmanService.calculate_solo_rewards(won, len(word), guessed_ratio)
        await db_service.add_user_coins(ctx.author.id, coins)
        
        if won:
            title = lang_service.get_text("hangman_solo_win_title", lang)
            desc = lang_service.get_text("hangman_solo_win_desc", lang, word=word, coins=coins)
            await ctx.send(embed=embed_service.success(title, desc))
        elif game_view.surrendered:
            title = lang_service.get_text("hangman_solo_surrender_title", lang)
            desc = lang_service.get_text("hangman_solo_surrender_desc", lang, word=word, coins=coins)
            await ctx.send(embed=embed_service.info(title, desc))
        else:
            title = lang_service.get_text("hangman_solo_lose_title", lang)
            desc = lang_service.get_text("hangman_solo_lose_desc", lang, word=word, coins=coins)
            await ctx.send(embed=embed_service.error(title, desc))

    async def _run_multiplayer_game(self, ctx: commands.Context, word_data: dict, lang: str, difficulty: str, category: str, players: list = None):
        # 1. Unirse a la partida (solo si no se proveen ya los jugadores de una ronda previa)
        if players is None:
            join_embed = embed_service.fun(
                lang_service.get_text("hangman_multi_join_title", lang),
                lang_service.get_text("hangman_multi_join_desc", lang, time=10)
            )
            join_msg = await ctx.send(embed=join_embed)
            await join_msg.add_reaction("🦅")
            
            await asyncio.sleep(10.0)
            
            try:
                join_msg = await ctx.channel.fetch_message(join_msg.id)
                reaction = discord.utils.get(join_msg.reactions, emoji="🦅")
            except Exception:
                reaction = None
                
            players = []
            if reaction:
                async for user in reaction.users():
                    if not user.bot:
                        players.append(user)
                        
            if len(players) < 2:
                try:
                    await join_msg.edit(embed=embed_service.error(
                        lang_service.get_text("title_error", lang),
                        lang_service.get_text("hangman_multi_no_players", lang)
                    ))
                except Exception:
                    await ctx.send(embed=embed_service.error(
                        lang_service.get_text("title_error", lang),
                        lang_service.get_text("hangman_multi_no_players", lang)
                    ))
                return
                
            try:
                await join_msg.delete()
            except Exception:
                pass
        
        # 2. Loop del juego
        word = word_data["word"]
        normalized_word = word_data["normalized_word"]
        hint = word_data["hint"]
        word_category = word_data["category"]
        
        scores = {p.id: 0 for p in players}
        player_names = {p.id: p.display_name for p in players}
        
        guessed_letters = set()
        guessed_word = ["_" if char.isalpha() else char for char in word]
        
        hint_revealed = False
        hint_letter = None
        
        def make_multi_embed(current_player, elapsed_time: float, guessed_word: list, hint: str, category: str, guessed_letters: set, hint_letter: str = None) -> discord.Embed:
            title = lang_service.get_text("hangman_game_title", lang)
            word_display = " ".join([f"`{c}`" for c in guessed_word])
            guessed_display = ", ".join([f"`{c.upper()}`" for c in sorted(guessed_letters)]) if guessed_letters else "---"
            
            scores_display = "\n".join([f"> **{player_names[pid]}:** {pts} pts" for pid, pts in sorted(scores.items(), key=lambda x: x[1], reverse=True)])
            
            remaining = max(0.0, 300.0 - elapsed_time)
            if remaining <= 60.0:
                hint_display = hint
            else:
                hint_display = lang_service.get_text("hangman_hint_hidden", lang)
                
            desc = (
                f"📝 **{lang_service.get_text('hangman_game_word', lang)}**\n"
                f"> {word_display}\n\n"
                f"📋 **Información de la Partida**\n"
                f"> 📂 **{lang_service.get_text('hangman_game_category', lang)}:** {category.capitalize()}\n"
                f"> 💡 **{lang_service.get_text('hangman_game_hint', lang)}:** {hint_display}\n"
                f"> ⏱️ **Tiempo de Juego:** {int(remaining)}s restantes\n\n"
                f"🔠 **{lang_service.get_text('hangman_game_guesses', lang)}**\n"
                f"> {guessed_display}\n\n"
                f"🏆 **Puntajes**\n"
                f"{scores_display}\n\n"
                f"🎯 **{lang_service.get_text('hangman_multi_turn', lang, user=current_player.mention)}**\n"
                f"💡 {lang_service.get_text('hangman_multi_turn_time', lang)}"
            )
            if hint_letter:
                pista_revelada_label = lang_service.get_text("hangman_hint_label", lang)
                desc = desc.replace("📋 Información de la Partida", f"💡 **{pista_revelada_label}:** `{hint_letter.upper()}`\n\n📋 Información de la Partida")
                
            return embed_service.fun(title, desc)
            
        start_time = asyncio.get_event_loop().time()
        current_player_idx = 0
        
        game_msg = await ctx.send(embed=make_multi_embed(players[0], 0, guessed_word, hint, word_category, guessed_letters, None))
        
        while "_" in guessed_word:
            elapsed = asyncio.get_event_loop().time() - start_time
            remaining = 300.0 - elapsed
            if remaining <= 0:
                await ctx.send(embed=embed_service.warning(
                    lang_service.get_text("hangman_multi_global_timeout", lang),
                    f"La palabra era: **{word}**"
                ))
                break
                
            # Revelar pista si queda 1 minuto o menos
            if remaining <= 60.0 and not hint_revealed:
                hint_revealed = True
                hint_letter = HangmanService.get_initial_hint(normalized_word, guessed_letters)
                if hint_letter:
                    guessed_letters.add(hint_letter)
                    for i, char in enumerate(normalized_word):
                        if char == hint_letter:
                            guessed_word[i] = word[i]
                    try:
                        hint_msg_text = lang_service.get_text("hangman_hint_revealed_chat", lang, letter=hint_letter.upper())
                        await ctx.send(hint_msg_text)
                    except Exception:
                        await ctx.send(f"💡 **Pista:** Se ha revelado la letra `{hint_letter.upper()}` al quedar menos de 1 minuto.")

            current_player = players[current_player_idx]
            
            try:
                await game_msg.edit(embed=make_multi_embed(current_player, elapsed, guessed_word, hint, word_category, guessed_letters, hint_letter if hint_revealed else None))
            except Exception:
                pass
                
            def check_multi(m):
                return m.author.id == current_player.id and m.channel.id == ctx.channel.id and len(m.content.strip()) > 0
                
            turn_timeout = min(remaining, 15.0)
            try:
                guess_msg = await self.bot.wait_for('message', check=check_multi, timeout=turn_timeout)
                try:
                    await guess_msg.delete()
                except Exception:
                    pass
                    
                guess = guess_msg.content.strip().lower()
                guess_norm = normalize_word(guess)
                
                if guess_norm.isalpha():
                    if len(guess_norm) == 1:
                        if guess_norm not in guessed_letters:
                            guessed_letters.add(guess_norm)
                            if guess_norm in normalized_word:
                                scores[current_player.id] += 1
                                for i, char in enumerate(normalized_word):
                                    if char == guess_norm:
                                        guessed_word[i] = word[i]
                    else:
                        if guess_norm == normalized_word:
                            scores[current_player.id] += 5
                            guessed_word = list(word)
            except asyncio.TimeoutError:
                pass
                
            current_player_idx = (current_player_idx + 1) % len(players)
            
        ranking = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        payouts_display = []
        for rank_pos, (pid, pts) in enumerate(ranking):
            if rank_pos == 0:
                coins = 30 + (pts * 2)
            elif rank_pos == 1:
                coins = 15 + (pts * 2)
            else:
                coins = 5 + (pts * 2)
                
            if coins <= 0 or pts == 0:
                coins = 2
                
            await db_service.add_user_coins(pid, coins)
            payouts_display.append(f"> **{player_names[pid]}**: {pts} pts ➔ 🪙 **{coins}** monedas")
            
        end_desc = lang_service.get_text("hangman_multi_end_desc", lang, word=word, ranking="\n".join(payouts_display))
        await ctx.send(embed=embed_service.success(
            lang_service.get_text("hangman_multi_end_title", lang),
            end_desc
        ))
        
        await asyncio.sleep(1.0)
        rematch_embed = embed_service.warning(
            lang_service.get_text("hangman_multi_rematch_title", lang),
            lang_service.get_text("hangman_multi_rematch_desc", lang)
        )
        rematch_msg = await ctx.send(embed=rematch_embed)
        await rematch_msg.add_reaction("🔄")
        
        # Esperar 10 segundos para la revancha
        await asyncio.sleep(10.0)
        
        try:
            rematch_msg = await ctx.channel.fetch_message(rematch_msg.id)
            reaction = discord.utils.get(rematch_msg.reactions, emoji="🔄")
        except Exception:
            reaction = None
            
        accepted_players = set()
        if reaction:
            async for user in reaction.users():
                if not user.bot:
                    accepted_players.add(user.id)
                    
        # Revancha aceptada si al menos uno de los participantes originales reacciona
        any_accepted = any(p.id in accepted_players for p in players)
        
        if any_accepted:
            await ctx.send(embed=embed_service.success(
                lang_service.get_text("title_success", lang),
                lang_service.get_text("hangman_multi_rematch_success", lang)
            ))
            
            word_data_new = await HangmanService.get_word(difficulty, category, lang, ctx.guild.id if ctx.guild else None)
            if word_data_new:
                # Volver a ejecutar el juego conservando los jugadores que jugaron (sin registrarse de nuevo)
                await self._run_multiplayer_game(ctx, word_data_new, lang, difficulty, category, players=players)
        else:
            await ctx.send(embed=embed_service.error(
                lang_service.get_text("title_error", lang),
                lang_service.get_text("hangman_multi_rematch_fail", lang),
                lite=True
            ))


async def setup(bot: commands.Bot):
    """Función de entrada para cargar el Cog en el bot."""
    await bot.add_cog(Diversion(bot))