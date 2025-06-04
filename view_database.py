#!/usr/bin/env python3
"""
Database Viewer for Costco Receipt App
Run this script to view all data in the database
"""

import sqlite3
from datetime import datetime

def view_all_data():
    """Display all data from the database in a readable format"""
    
    try:
        # Connect to database
        conn = sqlite3.connect('costco_receipts.db')
        cursor = conn.cursor()
        
        print("=" * 80)
        print("COSTCO RECEIPT DATABASE - ALL DATA")
        print("=" * 80)
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            print("❌ No database tables found. Run the app first to create tables.")
            return
        
        print(f"📁 Found tables: {[table[0] for table in tables]}")
        print()
        
        # Show Receipt data
        print("🧾 RECEIPTS:")
        print("-" * 60)
        cursor.execute("""
            SELECT id, store_number, store_address, upload_date, receipt_date 
            FROM receipt ORDER BY upload_date DESC
        """)
        receipts = cursor.fetchall()
        
        if not receipts:
            print("   No receipts found yet.")
        else:
            print(f"   Total receipts: {len(receipts)}")
            print()
            for receipt in receipts:
                receipt_id, store_num, address, upload_date, receipt_date = receipt
                print(f"   Receipt #{receipt_id}")
                print(f"   Store: {store_num}")
                print(f"   Address: {address}")
                print(f"   Uploaded: {upload_date}")
                print(f"   Receipt Date: {receipt_date}")
                print()
        
        # Show Receipt Items data
        print("🛒 RECEIPT ITEMS:")
        print("-" * 60)
        cursor.execute("""
            SELECT ri.id, ri.receipt_id, ri.item_number, ri.description, 
                   ri.original_price, ri.discount, ri.price, ri.date_recorded,
                   r.store_number
            FROM receipt_item ri 
            JOIN receipt r ON ri.receipt_id = r.id
            ORDER BY ri.receipt_id, ri.item_number
        """)
        items = cursor.fetchall()
        
        if not items:
            print("   No items found yet.")
        else:
            print(f"   Total items: {len(items)}")
            print()
            current_receipt = None
            for item in items:
                item_id, receipt_id, item_num, desc, orig_price, discount, final_price, date_rec, store = item
                
                if current_receipt != receipt_id:
                    current_receipt = receipt_id
                    print(f"   📄 Receipt #{receipt_id} - {store}")
                    print("   " + "-" * 50)
                
                print(f"   Item #{item_num}: {desc}")
                if discount > 0:
                    print(f"   💰 Price: ${orig_price:.2f} - ${discount:.2f} discount = ${final_price:.2f}")
                else:
                    print(f"   💰 Price: ${final_price:.2f}")
                print(f"   📅 Recorded: {date_rec}")
                print()
        
        # Summary statistics
        print("📊 SUMMARY STATISTICS:")
        print("-" * 60)
        
        # Total receipts
        cursor.execute("SELECT COUNT(*) FROM receipt")
        total_receipts = cursor.fetchone()[0]
        
        # Total items
        cursor.execute("SELECT COUNT(*) FROM receipt_item")
        total_items = cursor.fetchone()[0]
        
        # Total spent
        cursor.execute("SELECT SUM(price) FROM receipt_item")
        total_spent = cursor.fetchone()[0] or 0
        
        # Total discounts
        cursor.execute("SELECT SUM(discount) FROM receipt_item")
        total_discounts = cursor.fetchone()[0] or 0
        
        # Most expensive item
        cursor.execute("""
            SELECT item_number, description, price 
            FROM receipt_item 
            ORDER BY price DESC LIMIT 1
        """)
        most_expensive = cursor.fetchone()
        
        # Most discounted item
        cursor.execute("""
            SELECT item_number, description, discount 
            FROM receipt_item 
            WHERE discount > 0
            ORDER BY discount DESC LIMIT 1
        """)
        most_discounted = cursor.fetchone()
        
        print(f"   📄 Total Receipts: {total_receipts}")
        print(f"   🛒 Total Items: {total_items}")
        print(f"   💵 Total Spent: ${total_spent:.2f}")
        print(f"   💸 Total Discounts: ${total_discounts:.2f}")
        
        if most_expensive:
            print(f"   🔥 Most Expensive: {most_expensive[1]} (#{most_expensive[0]}) - ${most_expensive[2]:.2f}")
        
        if most_discounted:
            print(f"   🎯 Best Discount: {most_discounted[1]} (#{most_discounted[0]}) - ${most_discounted[2]:.2f} off")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

def view_item_history(item_number):
    """View price history for a specific item"""
    try:
        conn = sqlite3.connect('costco_receipts.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ri.price, ri.original_price, ri.discount, ri.date_recorded, 
                   r.store_number, r.store_address
            FROM receipt_item ri
            JOIN receipt r ON ri.receipt_id = r.id
            WHERE ri.item_number = ?
            ORDER BY ri.date_recorded DESC
        """, (item_number,))
        
        items = cursor.fetchall()
        
        if not items:
            print(f"❌ No history found for item #{item_number}")
            return
        
        print(f"📈 PRICE HISTORY FOR ITEM #{item_number}")
        print("-" * 60)
        
        for item in items:
            price, orig_price, discount, date_rec, store_num, store_addr = item
            print(f"📅 {date_rec}")
            print(f"🏪 {store_num} - {store_addr}")
            if discount > 0:
                print(f"💰 ${orig_price:.2f} - ${discount:.2f} discount = ${price:.2f}")
            else:
                print(f"💰 ${price:.2f}")
            print()
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # View specific item history
        item_number = sys.argv[1]
        view_item_history(item_number)
    else:
        # View all data
        view_all_data()
    
    print("\n" + "=" * 80)
    print("USAGE:")
    print("  python view_database.py           # View all data")
    print("  python view_database.py 1797100  # View history for specific item")
    print("=" * 80) 