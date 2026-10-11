actual = 185.84
tuesday = 13.14
monday_close = actual - tuesday

print(f"Actual Tuesday close: ${actual:.2f}")
print(f"Tuesday trades: ${tuesday:.2f}")  
print(f"Monday close was: ${monday_close:.2f}")
print()
print(f"You said Monday close: $154.58")
print(f"Difference: ${monday_close - 154.58:.2f}")
print()
print("CONCLUSION:")
print(f"Monday actually closed at ${monday_close:.2f}, not $154.58")
print(f"Tuesday P&L is correct: ${tuesday:.2f}")
