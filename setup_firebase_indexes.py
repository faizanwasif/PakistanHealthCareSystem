#!/usr/bin/env python3
"""
Firebase Index Setup Script
Run this to create required composite indexes for the application.
"""

import webbrowser
import sys

# Index URLs from the error logs
INDEX_URLS = [
    # notifications collection (user_id + created_at)
    "https://console.firebase.google.com/v1/r/project/innovista-final/firestore/indexes?create_composite=ClVwcm9qZWN0cy9pbm5vdmlzdGEtZmluYWwvZGF0YWJhc2VzLyhkZWZhdWx0KS9jb2xsZWN0aW9uR3JvdXBzL25vdGlmaWNhdGlvbnMvaW5kZXhlcy9fEAEaCwoHdXNlcl9pZBABGg4KCmNyZWF0ZWRfYXQQAhoMCghfX25hbWVfXxAC",
    
    # conversations collection (citizen_id + created_at)
    "https://console.firebase.google.com/v1/r/project/innovista-final/firestore/indexes?create_composite=ClVwcm9qZWN0cy9pbm5vdmlzdGEtZmluYWwvZGF0YWJhc2VzLyhkZWZhdWx0KS9jb2xsZWN0aW9uR3JvdXBzL2NvbnZlcnNhdGlvbnMvaW5kZXhlcy9fEAEaDgoKY2l0aXplbl9pZBABGg4KCmNyZWF0ZWRfYXQQAhoMCghfX25hbWVfXxAC",
    
    # sehat_card_applications collection (user_id + applied_at)
    "https://console.firebase.google.com/v1/r/project/innovista-final/firestore/indexes?create_composite=Cl9wcm9qZWN0cy9pbm5vdmlzdGEtZmluYWwvZGF0YWJhc2VzLyhkZWZhdWx0KS9jb2xsZWN0aW9uR3JvdXBzL3NlaGF0X2NhcmRfYXBwbGljYXRpb25zL2luZGV4ZXMvXxABGgsKB3VzZXJfaWQQARoOCgphcHBsaWVkX2F0EAIaDAoIX19uYW1lX18QAg"
]

def main():
    print("Firebase Index Setup")
    print("===================")
    print("This script will open Firebase Console URLs to create required indexes.")
    print("You need to:")
    print("1. Be logged into Firebase Console")
    print("2. Have access to the 'innovista-final' project")
    print("3. Click 'Create Index' on each opened page")
    print()
    
    input("Press Enter to continue...")
    
    for i, url in enumerate(INDEX_URLS, 1):
        print(f"Opening index {i}/3...")
        webbrowser.open(url)
        input(f"Index {i} opened. Create the index in Firebase Console, then press Enter to continue...")
    
    print("\n✅ All index URLs opened!")
    print("After creating all indexes, restart the server to resolve the query errors.")

if __name__ == "__main__":
    main()
