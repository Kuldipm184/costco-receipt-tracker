import re

# Simulate the exact OCR text from the receipt
ocr_text = """Print Receipt
CoSrc@
=WHOLESALE
SOUTHLAKE #669
2601 E STATE HIGHWAY 114
SOUTHLAKE, TX 76092
21066920203982505162035
Member 112012374503
E
933402
DORITOS 30Z
6.99 N
352823
933402
2.00-
E
891742
COKEZERO35**
17.69
1840300
UBCARGOSHORT
50.97 Y
354812
/1840300
12.00-
E
1018249
ORG ATAULFO
7.99 N
E
18600
MANDARINS
6.79 N
E
910270
ORG GRE BEAN
6.99 N
1856546
GERRY 1/4ZIP
25.98 Y
354765
/1856546
6.00-
E
1008
18 CT EGGS
5.19 N
E
1294443
KS CHKN
18.49 N
SUBTOTAL
127.08
TAX
6.32
****
TOTAL
[133v4"""

def parse_costco_format(lines):
    """Parse Costco-specific receipt format with E indicators and various discount patterns"""
    parsed_entries = []
    i = 0
    
    # First pass: Parse all entries into structured format
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for 'E' indicator (start of item)
        if line == 'E' and i + 3 < len(lines):
            try:
                item_number_line = lines[i + 1].strip()
                description_line = lines[i + 2].strip()
                price_line = lines[i + 3].strip()
                
                # Validate item number (6-8 digits)
                if re.match(r'^\d{6,8}$', item_number_line):
                    # Extract price and currency indicator
                    price_match = re.match(r'^(\d+\.\d{2})\s*([NY-]?)$', price_line)
                    if price_match:
                        amount = float(price_match.group(1))
                        currency_indicator = price_match.group(2) or 'N'
                        
                        # Determine entry type based on description and currency indicator
                        if description_line.startswith('/'):
                            # This is a discount entry
                            parsed_entries.append({
                                "type": "discount",
                                "discount_code": item_number_line,
                                "referenced_product": description_line[1:],  # Remove the '/' prefix
                                "discount_amount": amount,
                                "currency_indicator": currency_indicator
                            })
                        else:
                            # This is a regular item
                            parsed_entries.append({
                                "type": "item",
                                "product_code": item_number_line,
                                "description": description_line,
                                "amount": amount,
                                "currency_indicator": currency_indicator
                            })
                        
                        i += 4
                        continue
            except (ValueError, IndexError):
                pass
        
        # Handle discount pattern: discount_code, product_code, discount_amount- (CHECK THIS FIRST!)
        elif (re.match(r'^\d{6,8}$', line) and i + 2 < len(lines) and
              re.match(r'^\d{6,8}$', lines[i + 1].strip()) and
              re.match(r'^\d+\.\d{2}-$', lines[i + 2].strip())):
            try:
                discount_code = line
                product_code = lines[i + 1].strip()
                discount_amount_str = lines[i + 2].strip()
                
                # Extract discount amount (remove the '-' at the end)
                discount_amount = float(discount_amount_str[:-1])
                
                parsed_entries.append({
                    "type": "standalone_discount",
                    "discount_code": discount_code,
                    "referenced_product": product_code,
                    "discount_amount": discount_amount
                })
                
                print(f"Found discount pattern: Discount code {discount_code}, Product {product_code}, Amount ${discount_amount:.2f}")
                
                i += 3
                continue
            except (ValueError, IndexError):
                pass
        
        # Handle items without 'E' prefix - look for product code, description, price pattern
        elif (re.match(r'^\d{4,8}$', line) and i + 2 < len(lines) and
              not re.match(r'^\d+\.\d{2}', lines[i + 1].strip()) and  # Description shouldn't start with price
              (re.match(r'^\d+\.\d{2}\s*[NY]?$', lines[i + 2].strip()) or  # Regular price
               re.match(r'^\d+\.\d{2}-$', lines[i + 2].strip()))):  # OR discount amount with dash
            try:
                item_number_line = line
                description_line = lines[i + 1].strip()
                price_line = lines[i + 2].strip()
                
                # Check if this is a discount amount (ends with -)
                if re.match(r'^\d+\.\d{2}-$', price_line):
                    # This is a discount entry
                    discount_amount = float(price_line[:-1])  # Remove the '-'
                    
                    if description_line.startswith('/'):
                        # This is an inline discount
                        parsed_entries.append({
                            "type": "discount",
                            "discount_code": item_number_line,
                            "referenced_product": description_line[1:],  # Remove the '/' prefix
                            "discount_amount": discount_amount,
                            "currency_indicator": "-"
                        })
                        print(f"Found inline discount: Discount code {item_number_line}, Product {description_line[1:]}, Amount ${discount_amount:.2f}")
                    else:
                        # This might be a standalone discount without the 3-line pattern
                        parsed_entries.append({
                            "type": "standalone_discount",
                            "discount_code": item_number_line,
                            "referenced_product": description_line,  # Description is the product code
                            "discount_amount": discount_amount
                        })
                        print(f"Found standalone discount (2-line): Discount code {item_number_line}, Product {description_line}, Amount ${discount_amount:.2f}")
                else:
                    # Regular item
                    price_match = re.match(r'^(\d+\.\d{2})\s*([NY-]?)$', price_line)
                    if price_match:
                        amount = float(price_match.group(1))
                        currency_indicator = price_match.group(2) or 'N'
                        
                        # This is a regular item
                        parsed_entries.append({
                            "type": "item",
                            "product_code": item_number_line,
                            "description": description_line,
                            "amount": amount,
                            "currency_indicator": currency_indicator
                        })
                
                i += 3
                continue
            except (ValueError, IndexError):
                pass
        
        i += 1
    
    return parsed_entries

# Test the parsing
lines = ocr_text.split('\n')
parsed_entries = parse_costco_format(lines)

print("=== PARSED ENTRIES ===")
for i, entry in enumerate(parsed_entries):
    print(f"{i}: {entry['type']} - Product: {entry.get('product_code', entry.get('referenced_product', 'N/A'))}, Amount: {entry.get('amount', entry.get('discount_amount', 'N/A'))}")

print("\n=== PROCESSING ITEMS AND APPLYING DISCOUNTS ===")

items = []
for i, entry in enumerate(parsed_entries):
    if entry["type"] == "item":
        product_info = {
            "item_number": entry["product_code"],
            "description": entry["description"],
            "price": entry["amount"],
            "original_price": entry["amount"],
            "discount": 0.0
        }
        
        print(f"\nProcessing item: {entry['product_code']} - {entry['description']} - ${entry['amount']:.2f}")
        
        # Look for discounts that apply to this item
        discount_amount = 0.0
        
        # Check for inline discount (next entry with "/" prefix)
        if (i + 1 < len(parsed_entries) and 
            parsed_entries[i + 1]["type"] == "discount" and
            parsed_entries[i + 1]["referenced_product"] == entry["product_code"]):
            discount_amount = parsed_entries[i + 1]["discount_amount"]
            print(f"  → Found inline discount: ${discount_amount:.2f} for {entry['product_code']}")
        
        # Check for standalone discount by matching product codes
        print(f"  → Checking for standalone discounts for product {entry['product_code']}...")
        for j, discount_entry in enumerate(parsed_entries):
            if discount_entry["type"] == "standalone_discount":
                print(f"    Discount entry {j}: code={discount_entry['discount_code']}, product={discount_entry['referenced_product']}, amount=${discount_entry['discount_amount']:.2f}")
                if discount_entry["referenced_product"] == entry["product_code"]:
                    discount_amount += discount_entry["discount_amount"]
                    print(f"    ✓ MATCH! Found standalone discount: ${discount_entry['discount_amount']:.2f} for product {entry['product_code']} (discount code: {discount_entry['discount_code']})")
                else:
                    print(f"    ✗ No match: {discount_entry['referenced_product']} != {entry['product_code']}")
        
        # Apply discount and calculate final price
        if discount_amount > 0:
            product_info["discount"] = discount_amount
            product_info["price"] = max(0, entry["amount"] - discount_amount)
            print(f"  → Applied discount: Original ${entry['amount']:.2f} - Discount ${discount_amount:.2f} = Final ${product_info['price']:.2f}")
        else:
            print(f"  → No discount applied")
        
        items.append(product_info)

print(f"\n=== FINAL RESULTS ===")
for item in items:
    if item['discount'] > 0:
        print(f"  {item['item_number']}: {item['description']} - Original: ${item['original_price']:.2f}, Discount: ${item['discount']:.2f}, Final: ${item['price']:.2f}")
    else:
        print(f"  {item['item_number']}: {item['description']} - ${item['price']:.2f}") 