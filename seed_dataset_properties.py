import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import csv
import json
import os
import re
import random
import requests

DATASET_DIR = r"C:\Users\Dell\Downloads\dataset_real-estate"
AMENITIES_CSV = os.path.join(DATASET_DIR, "facets", "facets", "AMENITIES.csv")

# 1. Load Amenities Dictionary
amenities_map = {}
if os.path.exists(AMENITIES_CSV):
    with open(AMENITIES_CSV, mode="r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            amenities_map[row["id"].strip()] = row["label"].strip()

print(f"Loaded {len(amenities_map)} amenities from dictionary.")

# Image Galleries
PHOTO_POOLS = {
    'Apartment': [
        "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1502005229762-ae1b46000281?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1484154218962-a197022b5858?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=1200&q=80",
    ],
    'Penthouse': [
        "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1200&q=80",
    ],
    'Villa': [
        "https://images.unsplash.com/photo-1600585154526-990dced4db0d?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1600565193348-f74bd3c7ccdf?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1613977257363-707ba9348227?auto=format&fit=crop&w=1200&q=80",
    ],
    'Builder Floor': [
        "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1600573472591-ee6b68d14c68?auto=format&fit=crop&w=1200&q=80",
    ]
}

CITY_CENTERS = {
    'Mumbai': {'lat': 19.0760, 'lng': 72.8777, 'state': 'Maharashtra'},
    'Gurgaon': {'lat': 28.4595, 'lng': 77.0266, 'state': 'Haryana'},
    'Hyderabad': {'lat': 17.3850, 'lng': 78.4867, 'state': 'Telangana'},
    'Kolkata': {'lat': 22.5726, 'lng': 88.3639, 'state': 'West Bengal'},
}

def parse_price(price_str):
    if not price_str or not isinstance(price_str, str):
        return None
    price_str = price_str.replace(',', '').strip()
    # Match Cr / Crore
    cr_match = re.search(r'([\d\.]+)\s*(?:-\s*([\d\.]+))?\s*(?:Cr|Crore)', price_str, re.IGNORECASE)
    if cr_match:
        val1 = float(cr_match.group(1))
        val2 = float(cr_match.group(2)) if cr_match.group(2) else val1
        avg_cr = (val1 + val2) / 2.0
        return int(avg_cr * 10000000)
    # Match L / Lakh / Lac
    l_match = re.search(r'([\d\.]+)\s*(?:-\s*([\d\.]+))?\s*(?:L|Lakh|Lac)', price_str, re.IGNORECASE)
    if l_match:
        val1 = float(l_match.group(1))
        val2 = float(l_match.group(2)) if l_match.group(2) else val1
        avg_l = (val1 + val2) / 2.0
        return int(avg_l * 100000)
    # Plain numeric
    num_match = re.search(r'(\d+)', price_str)
    if num_match:
        val = int(num_match.group(1))
        if val > 500000:
            return val
    return None

def parse_area(area_str):
    if not area_str or not isinstance(area_str, str):
        return None
    clean = area_str.replace(',', '').lower()
    match = re.search(r'([\d\.]+)(?:\s*-\s*([\d\.]+))?', clean)
    if match:
        a1 = float(match.group(1))
        a2 = float(match.group(2)) if match.group(2) else a1
        return int((a1 + a2) / 2.0)
    return None

def parse_bhk(bhk_val):
    if not bhk_val:
        return 2
    try:
        val = int(float(bhk_val))
        return min(max(val, 1), 7)
    except:
        return 2

def parse_locality(loc_raw, default_city):
    if not loc_raw:
        return default_city
    # Locality dict format in string: "{'CITY': ..., 'LOCALITY_NAME': 'Bandra West'}"
    match = re.search(r"'LOCALITY_NAME':\s*'([^']+)'", loc_raw)
    if match:
        return match.group(1).strip()
    return default_city

# Authenticate with Spring Boot
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8085/api").rstrip("/")
print(f"Logging in to Spring Boot at {BACKEND_URL}...")
login_res = requests.post(f'{BACKEND_URL}/auth/login', json={'email': 'admin@estateiq.com', 'password': 'Password123'})
if login_res.status_code != 200:
    print("Login failed:", login_res.text)
    exit(1)
token = login_res.json()['data']['token']
headers = {'Authorization': f'Bearer {token}'}
print("Authenticated successfully.")

# Process CSVs
csv_sources = [
    {'city': 'Mumbai', 'file': os.path.join(DATASET_DIR, 'mumbai.csv'), 'limit': 10},
    {'city': 'Gurgaon', 'file': os.path.join(DATASET_DIR, 'gurgaon_10k.csv'), 'limit': 10},
    {'city': 'Hyderabad', 'file': os.path.join(DATASET_DIR, 'hyderabad.csv'), 'limit': 10},
    {'city': 'Kolkata', 'file': os.path.join(DATASET_DIR, 'kolkata.csv'), 'limit': 10},
]

total_seeded = 0

for source in csv_sources:
    city_name = source['city']
    file_path = source['file']
    limit = source['limit']
    city_meta = CITY_CENTERS[city_name]

    print(f"\nProcessing {city_name} from {file_path}...")
    if not os.path.exists(file_path):
        print(f"Skipping {file_path} - not found")
        continue

    seeded_for_city = 0
    with open(file_path, mode='r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if seeded_for_city >= limit:
                break

            # Parse fields
            price = parse_price(row.get('PRICE'))
            area = parse_area(row.get('AREA'))
            bhk = parse_bhk(row.get('BEDROOM_NUM'))

            if not price or price < 1500000 or price > 500000000:
                continue
            if not area or area < 300 or area > 15000:
                continue

            raw_heading = row.get('PROP_HEADING') or row.get('PROP_NAME') or row.get('DESCRIPTION') or ''
            raw_heading = raw_heading.split('\n')[0].strip()
            if len(raw_heading) < 10:
                raw_heading = f"Spacious {bhk} BHK Residence in {city_name}"

            locality = parse_locality(row.get('location'), city_name)
            prop_type_raw = (row.get('PROPERTY_TYPE') or 'Apartment').lower()
            if 'villa' in prop_type_raw or 'bungalow' in prop_type_raw or 'farm' in prop_type_raw:
                property_type = 'Villa'
            elif 'penthouse' in prop_type_raw:
                property_type = 'Penthouse'
            elif 'floor' in prop_type_raw:
                property_type = 'Builder Floor'
            else:
                property_type = 'Apartment'

            # Amenities
            raw_amenities = row.get('AMENITIES', '')
            mapped_amenities = [
                amenities_map.get(a.strip())
                for a in raw_amenities.split(',')
                if a.strip() in amenities_map and amenities_map.get(a.strip())
            ]
            if len(mapped_amenities) < 3:
                mapped_amenities.extend(['24/7 Security & CCTV', '100% Power Backup', 'Reserved Parking', 'High-speed Elevators'])
            mapped_amenities = list(dict.fromkeys(mapped_amenities))[:6]

            # Photos
            pool = PHOTO_POOLS.get(property_type, PHOTO_POOLS['Apartment'])
            images = random.sample(pool, min(3, len(pool)))

            # Coordinates with slight random jitter
            lat = city_meta['lat'] + round(random.uniform(-0.06, 0.06), 4)
            lng = city_meta['lng'] + round(random.uniform(-0.06, 0.06), 4)

            # Seller Assignment
            sellers = [
                {'name': 'Rajesh Singhania', 'email': 'seller@estateiq.com', 'phone': '+91 98210 55667', 'type': 'Owner'},
                {'name': 'Pooja Batra', 'email': 'agent@estateiq.com', 'phone': '+91 98200 44556', 'type': 'Agent'},
                {'name': 'Aarav Oberoi', 'email': 'seller@estateiq.com', 'phone': '+91 98211 99887', 'type': 'Builder'},
            ]
            seller = random.choice(sellers)

            match_score = random.randint(86, 98)
            fraud_score = random.randint(1, 8)

            property_doc = {
                'title': raw_heading[:90],
                'description': f"Authentic premium {bhk} BHK {property_type} in {locality}, {city_name}. Features {area} sq.ft. of carpet space, top ventilation, and verified title records.",
                'price': price,
                'propertyType': property_type,
                'location': locality,
                'city': city_name,
                'state': city_meta['state'],
                'bhk': bhk,
                'bathrooms': max(bhk, 1),
                'area': area,
                'furnishing': random.choice(['Fully Furnished', 'Semi-Furnished', 'Unfurnished']),
                'possession': random.choice(['Ready to Move', 'Ready to Move', 'Under Construction']),
                'constructionYear': random.randint(2020, 2025),
                'amenities': mapped_amenities,
                'images': images,
                'coordinates': {'lat': lat, 'lng': lng},
                'sellerName': seller['name'],
                'sellerEmail': seller['email'],
                'sellerPhone': seller['phone'],
                'sellerType': seller['type'],
                'status': 'active',
                'verified': True,
                'viewsCount': random.randint(450, 3200),
                'fraudScore': fraud_score,
                'matchPercentage': match_score,
                'matchReasons': [
                    f"Prime {locality} micro-market index",
                    f"Optimal {bhk} BHK layout for family or executive living",
                    "RERA compliance verified"
                ]
            }

            resp = requests.post('http://localhost:8085/api/properties', json=property_doc, headers=headers)
            if resp.status_code == 201:
                seeded_for_city += 1
                total_seeded += 1
                new_id = resp.json().get('id')
                print(f"  [+] Seeded {new_id}: {property_doc['title'][:40]} | ₹{price:,} | {city_name}")
            else:
                print(f"  [-] Failed to create property: {resp.status_code} - {resp.text[:100]}")

print(f"\n==========================================")
print(f"Completed dataset ingestion! Seeded {total_seeded} real properties.")
