import logging
import random
from config import settings
from services.core import database

logger = logging.getLogger(__name__)

_xp_cache = {}

def calculate_xp_required(level: int) -> int:
    """Calcula la XP necesaria para alcanzar el siguiente nivel."""
    return int(settings.LEVELS_CONFIG["XP_MULTIPLIER"] * (level ** settings.LEVELS_CONFIG["XP_EXPONENT"]))

class XpRepository:
    @classmethod
    async def add_xp(cls, guild_id: int, user_id: int, amount: int) -> tuple[int, bool]:
        """Añade XP a un usuario en memoria (Write-behind)."""
        key = (guild_id, user_id)
        
        import time
        if key not in _xp_cache:
            row = await database.fetch_one("SELECT xp, level, rebirths FROM guild_stats WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            if row:
                _xp_cache[key] = {'xp': row['xp'], 'level': row['level'], 'rebirths': row['rebirths'], 'dirty': False, 'last_access': time.time()}
            else:
                _xp_cache[key] = {'xp': 0, 'level': 1, 'rebirths': 0, 'dirty': False, 'last_access': time.time()}
        else:
            _xp_cache[key]['last_access'] = time.time()
        
        data = _xp_cache[key]
        data['xp'] += amount
        data['dirty'] = True 
        
        required = calculate_xp_required(data['level'])
        leveled_up = False
        
        # En la importación de db_service para monedas, lo llamaremos de forma dinámica para evitar circulares
        from services.repositories.user_repository import UserRepository
        
        while data['xp'] >= required:
            data['xp'] -= required
            data['level'] += 1
            leveled_up = True
            
            # Otorgar monedas por cada nivel subido
            coins_min, coins_max = settings.LEVELS_CONFIG.get("COINS_PER_LEVEL", (5, 10))
            coins_earned = random.randint(coins_min, coins_max)
            await UserRepository.add_user_coins(user_id, coins_earned)
            
            required = calculate_xp_required(data['level'])
        
        return data['level'], leveled_up

    @classmethod
    async def set_user_xp_level(cls, guild_id: int, user_id: int, xp: int, level: int, rebirths: int = None):
        """Establece directamente la XP, nivel y opcionalmente rebirths de un usuario, sincronizando caché."""
        key = (guild_id, user_id)
        
        # Guardar cualquier XP pendiente antes de sobrescribir
        if key in _xp_cache and _xp_cache[key]['dirty']:
            await cls.flush_xp_cache()
            
        if rebirths is None:
            if key in _xp_cache:
                rebirths = _xp_cache[key]['rebirths']
            else:
                row = await database.fetch_one("SELECT rebirths FROM guild_stats WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
                rebirths = row['rebirths'] if row else 0
                
        await database.execute(
            "INSERT INTO guild_stats (guild_id, user_id, xp, level, rebirths) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET xp = excluded.xp, level = excluded.level, rebirths = excluded.rebirths",
            (guild_id, user_id, xp, level, rebirths)
        )
        
        import time
        _xp_cache[key] = {
            'xp': xp,
            'level': level,
            'rebirths': rebirths,
            'dirty': False,
            'last_access': time.time()
        }

    @classmethod
    async def do_rebirth(cls, guild_id: int, user_id: int) -> tuple[bool, any]:
        """Realiza un renacimiento si el usuario es nivel 100+."""
        await cls.flush_xp_cache()
        
        row = await database.fetch_one("SELECT level, rebirths FROM guild_stats WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        if not row:
            return False, "no_data"
            
        min_level = settings.LEVELS_CONFIG["REBIRTH_LEVEL"]
        if row['level'] < min_level:
            return False, row['level']
        
        # Verificar monedas
        from services.repositories.user_repository import UserRepository
        cost = settings.LEVELS_CONFIG.get("REBIRTH_COST", 100)
        coins = await UserRepository.get_user_coins(user_id)
        if coins < cost:
            return False, "not_enough_coins"
        
        new_reb = row['rebirths'] + 1
        await UserRepository.add_user_coins(user_id, -cost)
        
        # Actualizar DB directamente
        await database.execute("UPDATE guild_stats SET level = 1, xp = 0, rebirths = ? WHERE guild_id = ? AND user_id = ?", (new_reb, guild_id, user_id))
        
        # Actualizar caché
        key = (guild_id, user_id)
        if key in _xp_cache:
            import time
            _xp_cache[key].update({'level': 1, 'xp': 0, 'rebirths': new_reb, 'dirty': False, 'last_access': time.time()})
            
        return True, new_reb

    @classmethod
    async def flush_xp_cache(cls):
        """Vuelca la XP acumulada en memoria a la base de datos física."""
        if not _xp_cache:
            return
            
        logger.debug(f"💾 Guardando XP en disco para {len(_xp_cache)} usuarios...")
        
        # Iterar sobre una copia segura
        for key, data in list(_xp_cache.items()):
            if not data['dirty']:
                continue
                
            guild_id, user_id = key
            saved_xp = data['xp']
            saved_lvl = data['level']
            saved_reb = data['rebirths']
            
            try:
                await database.execute(
                    "INSERT INTO guild_stats (guild_id, user_id, xp, level, rebirths) VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT(guild_id, user_id) DO UPDATE SET xp = excluded.xp, level = excluded.level, rebirths = excluded.rebirths",
                    (guild_id, user_id, saved_xp, saved_lvl, saved_reb)
                )
                
                # Marcar como limpia si no cambió en el transcurso de la escritura
                if key in _xp_cache:
                    if _xp_cache[key]['xp'] == saved_xp:
                        _xp_cache[key]['dirty'] = False
            except Exception:
                logger.exception(f"❌ Error guardando XP de {user_id} en guild {guild_id}")
        
        cls.clear_xp_cache_safe()

    @staticmethod
    def clear_xp_cache_safe(ttl: int = 600):
        """Limpia entradas de XP en memoria sin cambios pendientes y que han estado inactivas por más de 10 minutos (TTL)."""
        global _xp_cache
        import time
        now = time.time()
        keys_to_remove = [k for k, v in _xp_cache.items() if not v['dirty'] and (now - v.get('last_access', now) > ttl)]
        for k in keys_to_remove:
            del _xp_cache[k]

    @classmethod
    async def get_user_guild_data(cls, guild_id: int, user_id: int) -> dict:
        """Obtiene la XP, nivel y rebirths de un usuario (con caché write-behind)."""
        key = (guild_id, user_id)
        import time
        if key not in _xp_cache:
            row = await database.fetch_one("SELECT xp, level, rebirths FROM guild_stats WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            if row:
                _xp_cache[key] = {'xp': row['xp'], 'level': row['level'], 'rebirths': row['rebirths'], 'dirty': False, 'last_access': time.time()}
            else:
                _xp_cache[key] = {'xp': 0, 'level': 1, 'rebirths': 0, 'dirty': False, 'last_access': time.time()}
        else:
            _xp_cache[key]['last_access'] = time.time()
        return _xp_cache[key]

    @classmethod
    async def get_leaderboard(cls, guild_id: int, limit: int) -> list[dict]:
        """Obtiene la lista de los mejores usuarios ordenados por rebirths, level y xp (vuelca la caché primero)."""
        await cls.flush_xp_cache()
        rows = await database.fetch_all(
            "SELECT user_id, level, xp, rebirths FROM guild_stats WHERE guild_id = ? "
            "ORDER BY rebirths DESC, level DESC, xp DESC LIMIT ?",
            (guild_id, limit)
        )
        return [dict(row) for row in rows]

