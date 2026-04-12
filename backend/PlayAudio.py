import ctypes
import sys
import time
import os

def play_with_mci(path):
    # Standard Windows Multimedia IO call for near-instant playback
    mci = ctypes.windll.winmm
    
    # Use short path name to avoid spaces/unicode issues in MCI
    buffer = ctypes.create_unicode_buffer(260)
    ctypes.windll.kernel32.GetShortPathNameW(path, buffer, 260)
    short_path = buffer.value
    
    if not short_path:
        short_path = f'"{path}"'
        
    alias = "voice_chunk"
    
    # Close any previous accidental open
    mci.mciSendStringW(f"close {alias}", None, 0, None)
    
    # Open and Play
    res = mci.mciSendStringW(f"open {short_path} alias {alias}", None, 0, None)
    if res == 0:
        mci.mciSendStringW(f"play {alias} wait", None, 0, None)
        mci.mciSendStringW(f"close {alias}", None, 0, None)
        return True
    return False

def play_with_pygame(path):
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
        pygame.mixer.quit()
        return True
    except Exception as e:
        print(f"Pygame Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        audio_path = sys.argv[1]
        
        # Try MCI first (faster latency)
        success = play_with_mci(audio_path)
        
        # Fallback to Pygame if MCI fails
        if not success:
            play_with_pygame(audio_path)
            
    os._exit(0)
