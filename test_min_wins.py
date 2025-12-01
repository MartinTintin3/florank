import utils
import db

try:
    print("Testing with min_wins=1 (default)")
    active_wrestlers_1 = utils.get_active_wrestlers()
    print(f"Found {len(active_wrestlers_1)} active wrestlers.")
    
    print("\nTesting with min_wins=5")
    active_wrestlers_5 = utils.get_active_wrestlers(min_wins=5)
    print(f"Found {len(active_wrestlers_5)} active wrestlers.")

    print("\nTesting with min_wins=10")
    active_wrestlers_10 = utils.get_active_wrestlers(min_wins=10)
    print(f"Found {len(active_wrestlers_10)} active wrestlers.")

except Exception as e:
    print(f"Error: {e}")
