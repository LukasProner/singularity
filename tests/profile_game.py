# file: profile_game.py
# Profiling script pre časovú analýzu hernej logiky

import sys
import os
import cProfile
import pstats

# Tento riadok zabezpečí, že Python vie nájsť moduly projektu, ktoré sú o priečinok vyššie než skript profile_game.py.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tests.test_game_run import setup_module, test_initial_game, MockObject, setup_function
from singularity.code import g

def profile_test():
    """Profiluje test_initial_game() viackrát pre presnejšie meranie."""
    print("Spúšťam profiláciu...")
    print("=" * 60)
    
    setup_module()
    
    profiler = cProfile.Profile() #vytvorí profiler, ktorý sleduje, koľko času strávi každá funkcia.
    profiler.enable()
    
    # Spustite test viackrát pre presnejšie meranie
    iterations = 100
    print(f"Vykonávam test {iterations}x pre presnejšie meranie...")
    for i in range(iterations):
        print(f"  Iterácia {i+1}/{iterations}...")  # Odstránené end='\r'
        # Mock map_screen pre každú iteráciu (test ho resetuje)
        setup_function(test_initial_game)
        test_initial_game()
    
    profiler.disable()
    print("=" * 60)
    print("Profilácia dokončená!\n")
    print("TOP 20 NAJPOMALŠÍCH FUNKCIÍ (zoradené podľa kumulatívneho času):")
    print("=" * 60)
    stats = pstats.Stats(profiler) #vytvorí objekt pre analýzu nameraných dát.
    stats.sort_stats('cumulative') #zoradí funkcie podľa kumulatívneho času, teda koľko času trávia všetky vnútorné volania funkcií.
    stats.print_stats(40)
    
    print("\n" + "=" * 60)
    print("TOP 20 NAJPOMALŠÍCH FUNKCIÍ (zoradené podľa celkového času):")
    print("=" * 60)
    stats.sort_stats('tottime')
    stats.print_stats(40)

if __name__ == '__main__':
    profile_test()

    # python tests\profile_game.py