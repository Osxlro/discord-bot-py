import random
import logging
import unicodedata
import asyncio
import discord
from discord.ext import commands
from services.integrations import wordgame_api_service, translator_service
from services.core import lang_service, db_service
from services.utils import embed_service
from ui.games.hangman_ui import HangmanConfigView, HangmanGameView, HANGMAN_PICS
from config import settings

logger = logging.getLogger(__name__)

DIFFICULTY_MAP = {
    "fácil": {"min": 3, "max": 5},
    "medio": {"min": 6, "max": 8},
    "difícil": {"min": 9, "max": 20},
    "cualquiera": {"min": 3, "max": 20}
}

def normalize_word(word: str) -> str:
    """
    Normaliza una palabra convirtiéndola a minúsculas y removiendo acentos,
    pero preservando la letra 'ñ'.
    """
    word = word.lower().strip()
    result = []
    for char in word:
        if char in ('ñ', 'Ñ'):
            result.append('ñ')
        else:
            # Descomponer caracteres con acentos
            normalized = unicodedata.normalize('NFD', char)
            # Filtrar marcas de acentuación
            clean_char = "".join([c for c in normalized if not unicodedata.combining(c)])
            result.append(clean_char)
    return "".join(result)

async def translate_safe(text: str, target_lang: str) -> str:
    """Traductor con control de fallos."""
    if not text or target_lang == "en":
        return text
    try:
        res = await translator_service.traducir(text, target_lang)
        return res["traducido"]
    except Exception as e:
        logger.warning(f"Error al traducir '{text}' al idioma {target_lang}: {e}")
        return text

class HangmanService:
    # Historial de palabras usadas recientemente, organizadas por ID de servidor (guild_id)
    _recently_used_words = {}

    @classmethod
    async def get_word(cls, difficulty: str, category: str, lang: str, guild_id: int | None = None) -> dict | None:
        """
        Obtiene una palabra de la API, la traduce al idioma del servidor si es necesario,
        y genera sus versiones normalizadas, evitando repetir palabras recientemente jugadas en el servidor.
        """
        difficulty = difficulty.lower()
        category = category.lower()
        
        bounds = DIFFICULTY_MAP.get(difficulty, DIFFICULTY_MAP["cualquiera"])
        
        words = await wordgame_api_service.fetch_words(
            category=category,
            min_letters=bounds.get("min"),
            max_letters=bounds.get("max")
        )
        
        # Fallback si no hay palabras con los filtros
        if not words:
            logger.warning(f"No se encontraron palabras con filtros: dif={difficulty}, cat={category}. Reintentando sin filtros.")
            words = await wordgame_api_service.fetch_words()
            
        if not words:
            return None
            
        # Filtrar por palabras usadas recientemente en esta guild
        guild_key = guild_id or 0
        if guild_key not in cls._recently_used_words:
            cls._recently_used_words[guild_key] = []
        recent_list = cls._recently_used_words[guild_key]
        
        filtered_words = [w for w in words if normalize_word(w["word"]) not in recent_list]
        if not filtered_words:
            logger.info(f"Todas las palabras disponibles de la API fueron usadas recientemente en guild {guild_key}. Ignorando filtro temporalmente.")
            filtered_words = words
            
        word_data = random.choice(filtered_words)
        original_word = word_data["word"]
        original_hint = word_data.get("hint", "No hint available.")
        
        # Traducir si el idioma de destino no es inglés
        if lang != "en":
            translated_word = await translate_safe(original_word, lang)
            translated_hint = await translate_safe(original_hint, lang)
        else:
            translated_word = original_word
            translated_hint = original_hint
            
        # Limpiar caracteres raros y normalizar
        translated_word = translated_word.strip()
        normalized_word = normalize_word(translated_word)
        
        # Guardar en el historial de esta guild
        norm_chosen = normalize_word(translated_word)
        if norm_chosen not in recent_list:
            recent_list.append(norm_chosen)
            if len(recent_list) > 30:
                recent_list.pop(0)
                
        return {
            "original_word": original_word,
            "original_hint": original_hint,
            "word": translated_word,
            "hint": translated_hint,
            "normalized_word": normalized_word,
            "category": word_data.get("category", category)
        }

    @staticmethod
    def get_initial_hint(word_normalized: str, guessed_letters: set = None) -> str:
        """
        Retorna una letra al azar de la palabra como pista inicial,
        excluyendo aquellas letras que ya hayan sido adivinadas (si se especifican).
        """
        letters = [c for c in word_normalized if c.isalpha()]
        if guessed_letters:
            letters = [c for c in letters if c not in guessed_letters]
        if not letters:
            return ""
        return random.choice(letters)

    @staticmethod
    def calculate_solo_rewards(won: bool, word_len: int, guessed_ratio: float) -> int:
        """Calcula las monedas a pagar en modo SOLO."""
        if won:
            # Victoria: Recompensa media (20 a 40 monedas según longitud)
            return random.randint(20, 30) + min(word_len, 10)
        else:
            # Derrota: Recompensa baja basada en qué tan cerca estuvo
            return round(guessed_ratio * 10)

    @classmethod
    async def run_game(cls, ctx: commands.Context) -> None:
        """
        Orquesta el inicio del juego del Ahorcado, desde la vista de configuración
        hasta delegar la ejecución al modo seleccionado.
        """
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        # 1. Configuración de partida
        config_view = HangmanConfigView(ctx.author, lang)
        embed = config_view.get_embed()
        config_view.message = await ctx.reply(embed=embed, view=config_view)
        
        await config_view.wait()
        
        if config_view.status != "start":
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
            
        word_data = await cls.get_word(difficulty, category, lang, ctx.guild.id if ctx.guild else None)
        if not word_data:
            await ctx.send(embed=embed_service.error(
                lang_service.get_text("title_error", lang),
                lang_service.get_text("hangman_error_fetch", lang),
                lite=True
            ))
            return
            
        # 2. Ejecutar juego
        if mode == "solo":
            await cls.run_solo_game(ctx, word_data, lang)
        else:
            await cls.run_multiplayer_game(ctx, word_data, lang, difficulty, category)

    @classmethod
    async def run_solo_game(cls, ctx: commands.Context, word_data: dict, lang: str) -> None:
        """Ejecuta el bucle del juego en modo SOLO."""
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
                
            info_label = lang_service.get_text("hangman_game_info", lang)
            time_label = lang_service.get_text("hangman_game_time", lang)
            remaining_val = max(0, int(remaining))
            remaining_display = lang_service.get_text("hangman_time_remaining", lang, time=remaining_val)
            
            desc = (
                f"{pic}\n"
                f"📝 **{lang_service.get_text('hangman_game_word', lang)}**\n"
                f"> {word_display}\n\n"
                f"{info_label}\n"
                f"> 📂 **{lang_service.get_text('hangman_game_category', lang)}:** {category.capitalize()}\n"
                f"> 💡 **{lang_service.get_text('hangman_game_hint', lang)}:** {hint_display}\n"
                f"> ❤️ **{lang_service.get_text('hangman_game_lives', lang)}:** {lives} / 6\n"
                f"> {time_label}: {remaining_display}\n\n"
                f"🔠 **{lang_service.get_text('hangman_game_guesses', lang)}**\n"
                f"> {guessed_display}\n"
            )
            if hint_letter:
                pista_revelada_label = lang_service.get_text("hangman_hint_label", lang)
                desc = desc.replace(info_label, f"💡 **{pista_revelada_label}:** `{hint_letter.upper()}`\n\n{info_label}")
                
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
                    hint_letter = cls.get_initial_hint(normalized_word, guessed_letters)
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
                    guess_msg = await ctx.bot.wait_for('message', check=check, timeout=timeout_val)
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
        
        coins = cls.calculate_solo_rewards(won, len(word), guessed_ratio)
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

    @classmethod
    async def run_multiplayer_game(cls, ctx: commands.Context, word_data: dict, lang: str, difficulty: str, category: str, players: list = None) -> None:
        """Ejecuta el bucle del juego en modo MULTIPLAYER."""
        register_emoji = settings.DIVERSION_CONFIG["HANGMAN_EMOJIS"]["REGISTER"]
        rematch_emoji = settings.DIVERSION_CONFIG["HANGMAN_EMOJIS"]["REMATCH"]
        
        # 1. Unirse a la partida (solo si no se proveen ya los jugadores de una ronda previa)
        if players is None:
            join_embed = embed_service.fun(
                lang_service.get_text("hangman_multi_join_title", lang),
                lang_service.get_text("hangman_multi_join_desc", lang, time=10)
            )
            join_msg = await ctx.send(embed=join_embed)
            await join_msg.add_reaction(register_emoji)
            
            await asyncio.sleep(10.0)
            
            try:
                join_msg = await ctx.channel.fetch_message(join_msg.id)
                reaction = discord.utils.get(join_msg.reactions, emoji=register_emoji)
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
                
            info_label = lang_service.get_text("hangman_game_info", lang)
            time_label = lang_service.get_text("hangman_game_time", lang)
            remaining_val = max(0, int(remaining))
            remaining_display = lang_service.get_text("hangman_time_remaining", lang, time=remaining_val)
            scores_label = lang_service.get_text("hangman_scores", lang)
            
            desc = (
                f"📝 **{lang_service.get_text('hangman_game_word', lang)}**\n"
                f"> {word_display}\n\n"
                f"{info_label}\n"
                f"> 📂 **{lang_service.get_text('hangman_game_category', lang)}:** {category.capitalize()}\n"
                f"> 💡 **{lang_service.get_text('hangman_game_hint', lang)}:** {hint_display}\n"
                f"> {time_label}: {remaining_display}\n\n"
                f"🔠 **{lang_service.get_text('hangman_game_guesses', lang)}**\n"
                f"> {guessed_display}\n\n"
                f"{scores_label}\n"
                f"{scores_display}\n\n"
                f"🎯 **{lang_service.get_text('hangman_multi_turn', lang, user=current_player.mention)}**\n"
                f"💡 {lang_service.get_text('hangman_multi_turn_time', lang)}"
            )
            if hint_letter:
                pista_revelada_label = lang_service.get_text("hangman_hint_label", lang)
                desc = desc.replace(info_label, f"💡 **{pista_revelada_label}:** `{hint_letter.upper()}`\n\n{info_label}")
                
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
                    lang_service.get_text("hangman_word_was", lang, word=word)
                ))
                break
                
            # Revelar pista si queda 1 minuto o menos
            if remaining <= 60.0 and not hint_revealed:
                hint_revealed = True
                hint_letter = cls.get_initial_hint(normalized_word, guessed_letters)
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
                guess_msg = await ctx.bot.wait_for('message', check=check_multi, timeout=turn_timeout)
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
        await rematch_msg.add_reaction(rematch_emoji)
        
        # Esperar 10 segundos para la revancha
        await asyncio.sleep(10.0)
        
        try:
            rematch_msg = await ctx.channel.fetch_message(rematch_msg.id)
            reaction = discord.utils.get(rematch_msg.reactions, emoji=rematch_emoji)
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
            
            word_data_new = await cls.get_word(difficulty, category, lang, ctx.guild.id if ctx.guild else None)
            if word_data_new:
                # Volver a ejecutar el juego conservando los jugadores que jugaron (sin registrarse de nuevo)
                await cls.run_multiplayer_game(ctx, word_data_new, lang, difficulty, category, players=players)
        else:
            await ctx.send(embed=embed_service.error(
                lang_service.get_text("title_error", lang),
                lang_service.get_text("hangman_multi_rematch_fail", lang),
                lite=True
            ))
