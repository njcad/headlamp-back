#!/usr/bin/env python3
"""Quick test script to query all services from the database."""

from repos import get_supabase


def main():
    print("Connecting to Supabase...")
    
    try:
        supabase = get_supabase()
        
        print("Querying services table...")
        response = supabase.table("services").select("*").execute()
        
        services = response.data
        
        print(f"\nFound {len(services)} service(s):\n")
        
        for service in services:
            print(service)
        
        print("\n✅ Done!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()

