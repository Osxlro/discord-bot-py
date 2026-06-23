import wavelink
import asyncio
from config import settings

FILTERS_CONFIG = {
    "bassboost": {"type": "equalizer", "bands": [(0, 0.3), (1, 0.25), (2, 0.2), (3, 0.1), (4, 0.05)]},
    "superbass": {"type": "equalizer", "bands": [(0, 0.5), (1, 0.4), (2, 0.3), (3, 0.2), (4, 0.1)]},
    "hifi":      {"type": "equalizer", "bands": [(0, 0.15), (1, 0.1), (2, 0.05), (12, 0.05), (13, 0.1), (14, 0.15)]},
    "surround":  {"type": "rotation", "rotation_hz": 0.02},
    "metal":     {"type": "equalizer", "bands": [(0, 0.3), (1, 0.2), (2, 0.1), (3, -0.1), (4, -0.2), (5, -0.1), (6, 0.0), (7, 0.1), (8, 0.2), (9, 0.3), (10, 0.35), (11, 0.4), (12, 0.4), (13, 0.4), (14, 0.4)]},
    "pop":       {"type": "equalizer", "bands": [(0, -0.05), (1, 0.1), (2, 0.2), (3, 0.15), (4, 0.05)]},
    "soft":      {"type": "lowpass", "smoothing": 20.0},
    "treble":    {"type": "equalizer", "bands": [(10, 0.1), (11, 0.2), (12, 0.25), (13, 0.3)]},
    "nightcore": {"type": "timescale", "speed": 1.25, "pitch": 1.25},
    "vaporwave": {"type": "timescale", "speed": 0.85, "pitch": 0.8},
    "8d":        {"type": "rotation", "rotation_hz": 0.2},
    "karaoke":   {"type": "karaoke"},
    "tremolo":   {"type": "tremolo", "frequency": 2.0, "depth": 0.5},
    "vibrato":   {"type": "vibrato", "frequency": 2.0, "depth": 0.5},
    "flat":      {"type": "clear"}
}

async def apply_filter(player: wavelink.Player, filter_name: str) -> bool:
    """Aplica un preset de filtros al reproductor."""
    config = FILTERS_CONFIG.get(filter_name.lower())
    if not config: return False

    filters = wavelink.Filters()
    
    if config["type"] == "clear":
        await player.set_filters(filters)
        return True

    if config["type"] == "equalizer":
        bands = [{"band": b, "gain": g} for b, g in config["bands"]]
        filters.equalizer.set(bands=bands)
    
    elif config["type"] == "timescale":
        filters.timescale.set(
            speed=config.get("speed", 1.0),
            pitch=config.get("pitch", 1.0)
        )
    
    elif config["type"] == "rotation":
        filters.rotation.set(rotation_hz=config.get("rotation_hz", 0.2))
        
    elif config["type"] == "karaoke":
        filters.karaoke.set(
            level=1.0,
            mono_level=1.0,
            filter_band=220.0,
            filter_width=100.0
        )
        
    elif config["type"] == "tremolo":
        filters.tremolo.set(
            frequency=config.get("frequency", 2.0),
            depth=config.get("depth", 0.5)
        )
        
    elif config["type"] == "lowpass":
        filters.low_pass.set(smoothing=config.get("smoothing", 20.0))
        
    elif config["type"] == "vibrato":
        filters.vibrato.set(
            frequency=config.get("frequency", 2.0),
            depth=config.get("depth", 0.5)
        )

    await player.set_filters(filters)
    return True

async def fade_in(player: wavelink.Player, duration_ms: int):
    """Simula un efecto de Fade-In ajustando el volumen gradualmente."""
    target_vol = player.volume
    if target_vol == 0: return
    if player.current and player.current.length < duration_ms: return

    last_set_vol = 0
    current_track = player.current
    
    await player.set_volume(0)
    
    steps = settings.MUSIC_CONFIG["FADE_IN_STEPS"]
    step_delay = (duration_ms / 1000) / steps
    vol_step = target_vol / steps
    
    if step_delay < 0.05:
        step_delay = 0.05
    
    for i in range(1, steps + 1):
        if not player.playing or player.current != current_track: return

        try:
            if not player.connected or player.paused: return
            if last_set_vol > 0 and abs(player.volume - last_set_vol) > settings.MUSIC_CONFIG["VOLUME_TOLERANCE"]: return

            await asyncio.sleep(step_delay)
            new_vol = int(vol_step * i)
            await player.set_volume(new_vol)
            last_set_vol = new_vol
        except Exception:
            return
    
    await player.set_volume(target_vol)
