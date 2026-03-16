#!/usr/bin/env python3
"""Test Zoho email connection."""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_zoho():
    from providers.zoho import ZohoEmailProvider
    
    email = os.getenv("MIKE_EMAIL")
    password = os.getenv("MIKE_EMAIL_PASSWORD")
    
    print(f"Testing Zoho connection for: {email}")
    print(f"Password length: {len(password)} chars")
    print("-" * 60)
    
    try:
        provider = ZohoEmailProvider(email_addr=email, password=password)
        print("✓ Provider created")
        
        print("\nFetching emails...")
        emails = await provider.list_emails(limit=5)
        
        print(f"✓ Found {len(emails)} emails\n")
        
        for i, email in enumerate(emails, 1):
            print(f"{i}. From: {email.from_addr}")
            print(f"   Subject: {email.subject}")
            print(f"   Date: {email.date}")
            print(f"   Preview: {email.body[:100]}...")
            print()
        
        print("✅ Zoho email connection working!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_zoho())
