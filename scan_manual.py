
import re

def extract_strings(filename, min_len=4):
    with open(filename, "rb") as f:
        data = f.read()
    
    # Extract visible chars
    result = ""
    for byte in data:
        if 32 <= byte <= 126:
            result += chr(byte)
        else:
            result += " "
            
    # Normalize spaces
    text = " ".join(result.split())
    
    # Search for keywords
    keywords = ["OHMS", "RES", "4-WIRE", "FOUR_WR", "TRUE_OHMS", "FRES", "OHMF"]
    print(f"Searching in {filename} ({len(data)} bytes)...")
    
    for kw in keywords:
        # Find context around keyword
        indices = [m.start() for m in re.finditer(kw, text)]
        print(f"\n--- matches for '{kw}' ({len(indices)}) ---")
        for idx in indices[:5]: # Show first 5
            start = max(0, idx - 50)
            end = min(len(text), idx + 50)
            print(f"...{text[start:end]}...")

if __name__ == "__main__":
    extract_strings("e:/Cal-Lab/8508A___umeng0300.pdf")
