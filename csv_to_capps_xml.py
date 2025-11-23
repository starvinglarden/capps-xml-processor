#!/usr/bin/env python3
"""
CAPPS XML Converter for AIMsi POS CSV Exports
Converts CSV transaction data to CAPPS-compliant XML format
Complies with SB 1317 requirements (all customer data fields = "on file")
Handles two-file processing: purchases.csv and serials.csv
"""

import csv
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from datetime import datetime
import argparse
import os
from pathlib import Path
import json
import re
import requests
import ssl
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

class CAPSSAdapter(HTTPAdapter):
    """
    Custom adapter for CAPSS API that requires legacy SSL settings.
    CAPSS uses older SSL configurations that require relaxed security settings.
    """
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        # Allow legacy ciphers
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        # Use TLS 1.2
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)

class BrandExtractor:
    """Extract brand names from item descriptions using AI or pattern matching"""
    
    # Common musical instrument brands for pattern matching fallback
    KNOWN_BRANDS = [
        # Guitars
        'FENDER', 'GIBSON', 'MARTIN', 'TAYLOR', 'YAMAHA', 'EPIPHONE', 'IBANEZ',
        'PRS', 'GRETSCH', 'RICKENBACKER', 'GUILD', 'WASHBURN', 'DEAN', 'JACKSON',
        'ESP', 'SCHECTER', 'CORT', 'TAKAMINE', 'OVATION', 'SEAGULL', 'BREEDLOVE',
        'JAY TURSER', 'SQUIER', 'MITCHELL', 'OSCAR SCHMIDT', 'LUNA', 'ALVAREZ',
        'GODIN', 'PARKER', 'MUSIC MAN', 'STERLING', 'CHAPMAN', 'SOLAR', 'HARLEY BENTON',
        
        # Keyboards/Pianos
        'ROLAND', 'KORG', 'CASIO', 'KAWAI', 'NORD', 'KURZWEIL', 'ALESIS',
        'AKAI', 'NOVATION', 'ARTURIA', 'NATIVE INSTRUMENTS', 'MOOG', 'SEQUENTIAL',
        'DAVE SMITH', 'BEHRINGER', 'STEINWAY', 'BALDWIN', 'WURLITZER',
        
        # Drums
        'PEARL', 'TAMA', 'LUDWIG', 'DW', 'GRETSCH', 'ZILDJIAN', 'SABIAN',
        'PAISTE', 'MEINL', 'EVANS', 'REMO', 'MAPEX', 'SONOR', 'PACIFIC',
        'SIMMONS', 'ALESIS', 'ROLAND', 'GIBRALTAR', 'TOCA', 'LP', 'LATIN PERCUSSION',
        
        # Audio Equipment  
        'MARSHALL', 'VOX', 'FENDER', 'ORANGE', 'MESA', 'MESA BOOGIE', 'PEAVEY',
        'LINE 6', 'BOSS', 'SHURE', 'SENNHEISER', 'AKG', 'AUDIO-TECHNICA',
        'BLUE', 'RODE', 'NEUMANN', 'MXL', 'MACKIE', 'PRESONUS', 'FOCUSRITE',
        'BEHRINGER', 'QSC', 'JBL', 'YAMAHA', 'TASCAM', 'ZOOM', 'BLACKSTAR',
        
        # Wind Instruments
        'SELMER', 'BUFFET', 'JUPITER', 'MENDINI', 'JEAN PAUL', 'BUNDY',
        'ARMSTRONG', 'GEMEINHARDT', 'BACH', 'CONN', 'KING', 'HOLTON', 'GETZEN',
        
        # Accessories/Other
        'DUNLOP', 'ERNIE BALL', 'DADDARIO', "D'ADDARIO", 'ELIXIR', 'GHS',
        'LEVY\'S', 'HERCULES', 'ON-STAGE', 'SKB', 'GATOR', 'HARDCASE', 'MONO',
        'KALA', 'CORDOBA', 'HOHNER', 'SUZUKI', 'TRAYNOR', 'RANDALL', 'CRATE'
    ]
    
    def __init__(self, api_key=None, api_provider='groq'):
        """
        Initialize the brand extractor
        
        Args:
            api_key: API key for the chosen provider (Groq or Gemini)
            api_provider: 'groq' for Groq (free), 'gemini' for Google Gemini (free tier)
        """
        self.api_key = api_key
        self.api_provider = api_provider.lower()
        self.cache = {}
        self.cache_file = Path.home() / '.capps_brand_cache.json'
        self.load_cache()
        
        # Compile regex patterns for known brands
        self.brand_patterns = []
        for brand in self.KNOWN_BRANDS:
            # Create pattern that matches the brand as whole words
            pattern = r'\b' + re.escape(brand) + r'\b'
            self.brand_patterns.append((brand, re.compile(pattern, re.IGNORECASE)))
    
    def load_cache(self):
        """Load cached brand extractions"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    self.cache = json.load(f)
        except:
            self.cache = {}
    
    def save_cache(self):
        """Save brand extraction cache"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except:
            pass
    
    def extract_brand_with_groq(self, description):
        """
        Use Groq's free API (Llama model) to extract brand
        
        Args:
            description: Item description string
            
        Returns:
            Extracted brand name or None
        """
        if not self.api_key or not requests:
            return None
        
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            prompt = f"""Extract ONLY the brand name from this musical instrument description.
Return just the brand name, nothing else. If no brand found, return UNKNOWN.

Description: {description}"""
            
            data = {
                "model": "llama-3.1-8b-instant",  # Fast, free model
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 20
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=5)
            
            
            if response.status_code == 200:
                result = response.json()
                brand = result['choices'][0]['message']['content'].strip().upper()
                # Clean up the response
                brand = brand.replace('"', '').replace("'", '').strip()
                if brand and brand != "UNKNOWN" and len(brand) < 50:
                    return brand
        except Exception as e:
            print(f"Groq API error: {e}")
        
        return None
    
    def extract_brand_with_gemini(self, description):
        """
        Use Google's Gemini API (free tier) to extract brand
        
        Args:
            description: Item description string
            
        Returns:
            Extracted brand name or None
        """
        if not self.api_key or not requests:
            return None
        
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={self.api_key}"
            headers = {
                "Content-Type": "application/json"
            }
            
            prompt = f"""Extract ONLY the brand name from this musical instrument description.
Return just the brand name in uppercase, nothing else. If no brand found, return UNKNOWN.

Description: {description}"""
            
            data = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 20
                }
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                brand = result['candidates'][0]['content']['parts'][0]['text'].strip().upper()
                # Clean up the response
                brand = brand.replace('"', '').replace("'", '').strip()
                if brand and brand != "UNKNOWN" and len(brand) < 50:
                    return brand
        except Exception as e:
            print(f"Gemini API error: {e}")
        
        return None
    
    def extract_brand_with_api(self, description):
        """
        Route to the appropriate API based on provider setting
        
        Args:
            description: Item description string
            
        Returns:
            Extracted brand name or None
        """
        if self.api_provider == 'groq':
            return self.extract_brand_with_groq(description)
        elif self.api_provider == 'gemini':
            return self.extract_brand_with_gemini(description)
        else:
            return None
    
    def extract_brand_with_patterns(self, description):
        """
        Use pattern matching to extract brand from description
        
        Args:
            description: Item description string
            
        Returns:
            Extracted brand name or 'UNKNOWN'
        """
        description_upper = description.upper()
        
        # Check for known brands
        for brand, pattern in self.brand_patterns:
            if pattern.search(description):
                return brand
        
        # Try to extract first meaningful word(s) as fallback
        # Remove common non-brand prefixes
        prefixes_to_skip = ['BROKEN', 'USED', 'NEW', 'VINTAGE', 'ANTIQUE', 'ELECTRIC', 
                           'ACOUSTIC', 'CLASSICAL', 'DIGITAL', 'ANALOG', 'PORTABLE']
        
        words = description.split()
        for i, word in enumerate(words):
            word_upper = word.upper()
            if word_upper not in prefixes_to_skip:
                # Check if this might be a brand (usually first non-descriptor word)
                if len(word) > 2 and word_upper not in ['THE', 'AND', 'WITH', 'FOR']:
                    # Check if it's followed by a model-like word
                    if i + 1 < len(words):
                        next_word = words[i + 1].upper()
                        # Common model indicators
                        if any(x in next_word for x in ['PAUL', 'STANDARD', 'CUSTOM', 'SPECIAL', 
                                                         'DELUXE', 'SERIES', 'MODEL']):
                            return word_upper
                    # Return the word if it looks like a brand
                    if word_upper.replace('-', '').replace('\'', '').isalnum():
                        return word_upper
        
        return 'UNKNOWN'
    
    def extract_brand(self, description):
        """
        Extract brand from description using cache, API, or patterns
        
        Args:
            description: Item description string
            
        Returns:
            Brand name string
        """
        if not description:
            return 'UNKNOWN'
        
        # Check cache first
        cache_key = description.upper().strip()
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Try API if available
        brand = None
        if self.api_key:
            brand = self.extract_brand_with_api(description)
        
        # Fall back to pattern matching
        if not brand:
            brand = self.extract_brand_with_patterns(description)
        
        # Cache the result
        self.cache[cache_key] = brand
        self.save_cache()
        
        return brand


class CAPPSConverter:
    def __init__(self, license_number, api_key=None, api_provider='groq', min_cost=100, days_lookback=5, include_isi_serials=False):
        """
        Initialize converter with store's license number

        Args:
            license_number: Your store's secondhand dealer license number
            api_key: Optional API key for brand extraction (Groq or Gemini)
            api_provider: 'groq' or 'gemini' (default: 'groq')
            min_cost: Minimum transaction cost to report (default: 100)
            days_lookback: Number of days to look back for transactions (default: 5)
            include_isi_serials: Whether to include ISI-serialized inventory items (default: False)
        """
        self.license_number = license_number
        self.min_cost = min_cost
        self.days_lookback = days_lookback
        self.include_isi_serials = include_isi_serials
        self.brand_extractor = BrandExtractor(api_key, api_provider)
        
        # Nested category mapping: category_map[category_id][subcategory_id]
        self.category_map = {
            '1': {  # Wind instruments
                '1': 'ACCORDION',
                '2': 'FLUTE',
                '3': 'CLARINET',
                '4': 'INSTRUMENT',  # Saxophones
                '7': 'HORN',
                '8': 'TRUMPET',
                '9': 'INSTRUMENT',  # Trombone
                '14': 'VIOLIN',
                '27': 'MUSICAL ACCESSORY',  # Reeds
                '28': 'MUSICAL ACCESSORY',  # Brass/Wind Acc
                '29': 'MUSICAL ACCESSORY',  # Strings Acc
                '31': 'MUSICAL ACCESSORY',  # Band Method Books
            },
            '2': {  # Effects
                '1': 'FOOT PEDAL- AUDIO EQUIPMENT',  # Stomp boxes
            },
            '3': {  # Guitars/Fretted
                '1': 'GUITAR',  # Acoustics
                '3': 'GUITAR',  # Electrics
                '4': 'BASS',
                '6': 'MUSICAL ACCESSORY',  # Electronic tuners
                '7': 'MUSICAL ACCESSORY',  # Pickups
                '10': 'BANJO',  # Banjo/Uke/Mando
                '11': 'MUSICAL ACCESSORY',  # Cases
                '19': 'MUSICAL ACCESSORY',  # Strings
                '20': 'MUSICAL ACCESSORY',  # Fret accessory
            },
            '4': {  # Amps
                '1': 'AMPLIFIER',  # Guitar amp
                '2': 'AMPLIFIER',  # Guitar speaker
                '3': 'AMPLIFIER',  # Gtr head/pwr amp
                '4': 'AMPLIFIER',  # Bass amp
                '5': 'AMPLIFIER',  # Bass speaker
                '6': 'AMPLIFIER',  # Bass head/pwr amp
                '19': 'PREAMPLIFIER',
                '20': 'MUSICAL ACCESSORY',  # Amp accessory
            },
            '5': {  # Drums/Percussion
                '1': 'DRUM',  # Drum sets
                '2': 'CYMBAL',
                '3': 'DRUM',  # Congas/handrums
                '4': 'DRUM',  # World percussion
                '5': 'DRUM',  # Snares
                '6': 'MUSICAL ACCESSORY',  # Drum sticks
                '7': 'DRUM',  # Electronic percussion
                '10': 'DRUM',  # Toms/bass drum
                '20': 'MUSICAL ACCESSORY',  # Percussion accessory
                '21': 'MUSICAL ACCESSORY',  # Drum head
                '22': 'MUSICAL ACCESSORY',  # Drum hardware
            },
            '6': {  # Rentals/Consignment
                '1': 'INSTRUMENT',  # Delinquent rentals
                '2': 'INSTRUMENT',  # Consignment
            },
            '7': {  # PA/Sound
                '1': 'SOUND EQUIPMENT',  # Mixers
                '3': 'SOUND EQUIPMENT',  # PA speaker
                '4': 'AMPLIFIER',  # PA power amp
                '5': 'SOUND EQUIPMENT',  # Signal processor
                '8': 'SOUND EQUIPMENT',  # Microphone
                '9': 'SOUND EQUIPMENT',  # Racks and snakes
                '10': 'SOUND EQUIPMENT',  # PA rentals
                '11': 'MUSICAL ACCESSORY',  # Microphone stands
                '12': 'RECORDING EQUIPMENT',
                '13': 'SOUND EQUIPMENT',  # Wireless systems
                '20': 'MUSICAL ACCESSORY',  # PA accessory
            },
            '9': {  # Keyboards
                '1': 'KEYBOARD',
                '2': 'DRUM MACHINE',  # Drum mach/seq/pads
                '3': 'AMPLIFIER',  # Keyboard amps
                '6': 'MODULE',  # Sound modules
                '20': 'MUSICAL ACCESSORY',  # Keyboard accessory
            },
            '10': {  # Fees
                '1': 'MUSICAL ACCESSORY',  # Handling charges
            },
            '12': {  # Accessories
                '1': 'MUSICAL ACCESSORY',  # Small goods
                '2': 'MUSICAL ACCESSORY',  # Harmonicas
                '3': 'MUSICAL ACCESSORY',  # Non-band books
                '4': 'MUSICAL ACCESSORY',  # Cables
                '5': 'MUSICAL ACCESSORY',  # Amp tubes
                '6': 'MUSICAL ACCESSORY',  # Guitar parts
                '7': 'MUSICAL ACCESSORY',  # Slides/capos
                '8': 'MUSICAL ACCESSORY',  # Guitar straps
                '9': 'METRONOME',
                '10': 'MUSICAL ACCESSORY',  # Adapters
                '11': 'MUSICAL ACCESSORY',  # Blank media
                '12': 'AMPLIFIER',  # Battery/HP guitar amps
                '13': 'MUSICAL ACCESSORY',  # Band merch
                '14': 'MUSICAL ACCESSORY',  # eBay
            },
            '22': {  # Books/Methods
                '1': 'MUSICAL ACCESSORY',  # Methods
                '2': 'MUSICAL ACCESSORY',  # Other fretted
                '3': 'MUSICAL ACCESSORY',  # Songbooks
            },
            '24': {  # Books
                '1': 'MUSICAL ACCESSORY',
                '2': 'MUSICAL ACCESSORY',
                '3': 'MUSICAL ACCESSORY',
                '4': 'MUSICAL ACCESSORY',
            },
            '25': {  # Books
                '1': 'MUSICAL ACCESSORY',
                '2': 'MUSICAL ACCESSORY',
                '3': 'MUSICAL ACCESSORY',
            },
            '26': {  # Books
                '1': 'MUSICAL ACCESSORY',
                '2': 'MUSICAL ACCESSORY',
                '3': 'MUSICAL ACCESSORY',
                '4': 'MUSICAL ACCESSORY',
                '5': 'MUSICAL ACCESSORY',
            },
        }
        # Color mapping
        self.color_map = {
            'BLACK': 'BLACK', 'WHITE': 'WHITE', 'RED': 'RED', 'BLUE': 'BLUE',
            'GREEN': 'GREEN', 'YELLOW': 'YELLOW', 'ORANGE': 'ORANGE', 'PURPLE': 'PURPLE',
            'BROWN': 'BROWN', 'GRAY': 'GRAY', 'GREY': 'GRAY', 'PINK': 'PINK',
            'SILVER': 'SILVER', 'GOLD': 'GOLD', 'TAN': 'TAN', 'BEIGE': 'TAN',
            'CREAM': 'WHITE', 'IVORY': 'WHITE', 'NATURAL': 'BROWN',
            'SUNBURST': 'BROWN', 'TOBACCO': 'BROWN', 'CHERRY': 'RED',
            'WINE': 'RED', 'BURGUNDY': 'RED', 'CRIMSON': 'RED',
            'NAVY': 'BLUE', 'TEAL': 'BLUE', 'TURQUOISE': 'BLUE',
            'VIOLET': 'PURPLE', 'LAVENDER': 'PURPLE',
            'CHARCOAL': 'GRAY', 'SLATE': 'GRAY',
            'AMBER': 'ORANGE', 'COPPER': 'ORANGE'
        }
    
    def parse_aimsi_datetime(self, datetime_str):
        """
        Parse AIMsi datetime format: "11/10/2025 11:50:05 AM"
        Convert to CAPPS format: "2025-11-10T11:50:05"
        """
        try:
            # Parse the datetime string
            dt = datetime.strptime(datetime_str.strip(), "%m/%d/%Y %I:%M:%S %p")
            # Return in CAPPS format
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
        except Exception as e:
            print(f"Error parsing datetime '{datetime_str}': {e}")
            # Return current time as fallback
            return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    
    def get_color(self, description):
        """Extract color from description, return 'Other' if none found"""
        desc_upper = ' ' + description.upper() + ' '
        
        for color_name, base_color in self.color_map.items():
            if ' ' + color_name + ' ' in desc_upper:
                return base_color
        
        return 'Other'
    
    def load_serials_data(self, serials_file):
        """
        Load serials CSV file and create lookup dictionary
        
        Args:
            serials_file: Path to LUCASSERIALS.CSV or similar serials export
            
        Returns:
            Dictionary mapping serial numbers to (description, subcategory)
        """
        serials_data = {}
        
        try:
            with open(serials_file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 11:
                        # Column 2 (index 1): Serial number
                        # Column 7 (index 6): Description
                        # Column 11 (index 10): Subcategory ID
                        serial = row[1].strip()
                        description = row[6].strip() if len(row) > 6 else ""
                        subcategory = row[10].strip() if len(row) > 10 else ""
                        
                        if serial:
                            serials_data[serial] = {
                                'description': description,
                                'subcategory': subcategory
                            }
        except Exception as e:
            print(f"Error loading serials file: {e}")
        
        print(f"Loaded {len(serials_data)} serial numbers with descriptions")
        return serials_data
        
    def create_xml_structure(self):
        """Create the base XML structure for CAPPS upload"""
        root = ET.Element('capssUpload')
        root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        bulk_data = ET.SubElement(root, 'bulkUploadData')
        bulk_data.set('licenseNumber', self.license_number)
        return root, bulk_data
    
    def add_customer_data(self, customer_elem):
        """
        Add customer data fields - all set to "on file" per SB 1317
        
        Args:
            customer_elem: XML element for customer data
        """
        # All customer fields must be "on file" per SB 1317
        ET.SubElement(customer_elem, 'custLastName').text = 'on file'
        ET.SubElement(customer_elem, 'custFirstName').text = 'on file'
        ET.SubElement(customer_elem, 'custMiddleName').text = 'on file'
        ET.SubElement(customer_elem, 'gender').text = 'on file'
        ET.SubElement(customer_elem, 'race').text = 'on file'
        ET.SubElement(customer_elem, 'hairColor').text = 'on file'
        ET.SubElement(customer_elem, 'eyeColor').text = 'on file'
        ET.SubElement(customer_elem, 'height').text = 'on file'
        ET.SubElement(customer_elem, 'weight').text = 'on file'
        
        # Date of birth - using placeholder date
        dob = ET.SubElement(customer_elem, 'dateOfBirth')
        dob.set("xsi:nil", "true")
        ET.SubElement(customer_elem, 'dateOfBirthText').text = 'on file'
        
        # Address fields
        ET.SubElement(customer_elem, 'streetAddress').text = 'on file'
        ET.SubElement(customer_elem, 'city').text = 'on file'
        ET.SubElement(customer_elem, 'state').text = 'on file'
        ET.SubElement(customer_elem, 'postalCode').text = 'on file'
        ET.SubElement(customer_elem, 'phoneNumber').text = 'on file'
        ET.SubElement(customer_elem, 'nonUSAddress').text = 'on file'
        
        # ID information
        id_elem = ET.SubElement(customer_elem, 'id')
        ET.SubElement(id_elem, 'type').text = 'on file'
        ET.SubElement(id_elem, 'number').text = 'on file'
        ET.SubElement(id_elem, 'dateOfIssueText').text = 'on file'
        ET.SubElement(id_elem, 'issueState').text = 'on file'
        ET.SubElement(id_elem, 'issueCountry').text = 'on file'
        ET.SubElement(id_elem, 'yearOfExpirationText').text = 'on file'
        
        # Signature and fingerprint (base64 encoded placeholders)
        # These should be replaced with actual captured data if available
        noFinger = ET.SubElement(customer_elem, 'noFinger')
        noFinger.set("xsi:nil", "true")
        ET.SubElement(customer_elem, 'noFingerText').text = 'on file'
        ET.SubElement(customer_elem, 'signature').text = 'on file'
        ET.SubElement(customer_elem, 'fingerprint').text = 'on file'
    
    def process_purchase_row(self, row, serials_data, bulk_data, employee_name, transaction_type='BUY'):
        """
        Process a purchase row from AIMsi export (no headers)

        Filtering rules (transaction is skipped if ANY condition is met):
        - Older than configured lookback period (days_lookback) or future-dated
        - Amount is less than minimum cost threshold (configurable)
        - Serial number starts with "ISI" (unless include_isi_serials is True)
        - Serial number not found in serials CSV or has empty/missing description

        Expected columns:
        0: Date+Time (e.g., "11/10/2025 11:50:05 AM")
        1: Transaction Number (primary key)
        2: Amount
        3: Category ID
        4: Serial Number

        Args:
            row: List from CSV reader
            serials_data: Dictionary of serial number data
            bulk_data: XML bulk upload data element
            employee_name: Name of employee processing transaction
            transaction_type: Type of transaction (BUY, PAWN, etc.)

        Returns:
            True if row was processed, False if skipped due to filters
        """
        if len(row) < 5:
            print(f"Skipping incomplete row: {row}")
            return False
        
        # Parse the row data
        datetime_str = row[0]
        transaction_number = row[1].strip().strip('"')
        amount = row[2].strip()
        category_id = row[3].strip()
        serial_number = row[4].strip().strip('"')
        
        # Check if transaction is within configured lookback period
        try:
            transaction_dt = datetime.strptime(datetime_str.strip(), "%m/%d/%Y %I:%M:%S %p")
            days_ago = (datetime.now() - transaction_dt).days

            if days_ago > self.days_lookback:
                # Transaction is older than lookback period, skip it
                return False
            elif days_ago < 0:
                # Transaction is in the future, skip it
                print(f"Warning: Transaction {transaction_number} has future date: {datetime_str}")
                return False
        except Exception as e:
            print(f"Error parsing date for transaction {transaction_number}: {e}")
            # If we can't parse the date, skip this transaction for safety
            return False

        # Filter 1: Check if amount meets minimum cost threshold
        try:
            amount_value = float(amount.replace('$', '').replace(',', '').strip())
            if amount_value < self.min_cost:
                # Skip transactions under minimum cost
                return False
        except (ValueError, AttributeError) as e:
            print(f"Warning: Could not parse amount '{amount}' for transaction {transaction_number}: {e}")
            # Skip if we can't parse the amount
            return False

        # Filter 2: Exclude items with serial numbers starting with "ISI" (unless configured to include them)
        if not self.include_isi_serials and serial_number and serial_number.upper().startswith('ISI'):
            # Skip ISI-serialized inventory
            return False

        # Filter 3: Validate serial number has matching description in serials data
        if not serial_number or serial_number not in serials_data:
            # Serial number missing or not found in serials CSV
            return False

        serial_info = serials_data[serial_number]
        description = serial_info.get('description', '').strip()

        if not description:
            # Serial found but has empty/missing description
            return False

        # Create property transaction
        transaction = ET.SubElement(bulk_data, 'propertyTransaction')
        
        # Transaction time
        transaction_time = self.parse_aimsi_datetime(datetime_str)
        ET.SubElement(transaction, 'transactionTime').text = transaction_time
        
        # Add customer data (all "on file")
        customer = ET.SubElement(transaction, 'customer')
        self.add_customer_data(customer)
        
        # Store information
        store = ET.SubElement(transaction, 'store')
        ET.SubElement(store, 'employeeName').text = employee_name
        
        # Items
        items = ET.SubElement(transaction, 'items')
        item = ET.SubElement(items, 'item')

        # Get subcategory from serials data (description already validated above)
        subcategory_id = serial_info.get('subcategory', '')
        
        # Extract brand from description
        brand = self.brand_extractor.extract_brand(description)
        
        # Determine article type from category/subcategory
        article = self.category_map.get(category_id, {}).get(subcategory_id, 'INSTRUMENT')
        
        # Required item fields
        ET.SubElement(item, 'type').text = transaction_type
        ET.SubElement(item, 'loanBuyNumber').text = transaction_number
        ET.SubElement(item, 'amount').text = amount
        ET.SubElement(item, 'article').text = article
        ET.SubElement(item, 'brand').text = brand
        ET.SubElement(item, 'model').text = description
        
        # Add serial number if  present
        if serial_number and serial_number != '0':
            ET.SubElement(item, 'serialNumber').text = serial_number
        
        # Description is required
        ET.SubElement(item, 'description').text = description

        # Other mandatory fields
        ET.SubElement(item, 'inscription').text = "None"
        ET.SubElement(item, 'ownerAppliedNumber').text = "None"
        ET.SubElement(item, 'pattern').text = "None"
        ET.SubElement(item, 'color').text = self.get_color(description)
        ET.SubElement(item, 'material').text = "Unknown"
        ET.SubElement(item, 'itemSize').text = "Unknown"
        ET.SubElement(item, 'sizeUnit').text = "Unknown"
        
        # Return True to indicate successful processing
        return True
    
    def upload_to_capss(self, xml_file_path, client_id, client_secret):
        """Upload XML to CAPSS via API"""
        import requests
        import urllib3

        # Disable SSL warnings since we're using verify=False
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        try:
            # Get access token
            token_url = "https://capss.doj.ca.gov/oauth/token"
            token_data = {
                "scope": "api",
                "grant_type": "client_credentials",
            }

            # Create session with custom SSL adapter
            session = requests.Session()
            session.mount("https://", CAPSSAdapter())

            # Get token
            token_response = session.post(
                token_url,
                data=token_data,
                auth=(client_id, client_secret),
                verify=False,
            )

            if token_response.status_code != 200:
                print(f"Failed to get token: {token_response.status_code}")
                print(f"Response: {token_response.text}")
                return False

            token = token_response.json()["access_token"]
            print(f"Token obtained successfully: {token[:20]}...")
            
            # Upload file
            upload_url = "https://capss.doj.ca.gov/api/bulkupload/save"
            headers = {"Authorization": f"Bearer {token}"}

            with open(xml_file_path, 'rb') as f:
                files = {"bulkUploadFile": f}
                upload_response = session.post(upload_url, headers=headers, files=files, verify=False)
            
            if upload_response.status_code == 202:
                result = upload_response.json()
                status_url = result.get("links", {}).get("href", "")
                print(f"✓ Upload accepted. Submission ID: {result['submission']['submissionId']}")
                
                # Check status
                if status_url:
                    import time
                    for i in range(10):  # Poll up to 10 times
                        time.sleep(2)
                        status_response = session.get(status_url, headers=headers, verify=False)
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            if status_data["status"] == "complete":
                                print("Processing complete!")
                                return True
                        elif status_response.status_code != 202:
                            print(f"Status check failed: {status_response.status_code}")
                            return False
                return True
            else:
                print(f"Upload failed: {upload_response.status_code}")
                print(upload_response.text)
                return False
                
        except Exception as e:
            print(f"CAPSS upload error: {e}")
            return False
    
    def convert_aimsi_to_xml(self, purchases_file, serials_file, employee_name='Store Employee', client_id=None, client_secret=None):
        """
        Convert AIMsi purchase and serials CSV files to CAPPS XML format
        
        Args:
            purchases_file: Path to purchases CSV file (no headers)
            serials_file: Path to serials CSV file with descriptions
            output_xml_path: Path for output XML file
            employee_name: Name of employee processing transactions
        """
        # Load serials data first
        print(f"Loading serials data from {serials_file}...")
        serials_data = self.load_serials_data(serials_file)
        
        # Create XML structure
        root, bulk_data = self.create_xml_structure()
        
        # Read purchases CSV and process rows
        print(f"Processing purchases from {purchases_file}...")
        isi_filter_msg = "INCLUDE ISI serials" if self.include_isi_serials else "Exclude ISI serials"
        print(f"Filters: Last {self.days_lookback} days, Amount >= ${self.min_cost}, {isi_filter_msg}, Valid serial with description")
        processed_count = 0
        skipped_count = 0
        filtered_count = 0

        with open(purchases_file, 'r', encoding='utf-8', errors='ignore') as csvfile:
            reader = csv.reader(csvfile)

            for row_num, row in enumerate(reader, 1):
                try:
                    if len(row) >= 5:  # Ensure we have all required columns
                        was_processed = self.process_purchase_row(row, serials_data, bulk_data, employee_name)
                        if was_processed:
                            processed_count += 1
                        else:
                            filtered_count += 1
                    else:
                        print(f"Row {row_num}: Skipping incomplete row with {len(row)} columns")
                        skipped_count += 1
                except Exception as e:
                    print(f"Row {row_num}: Error processing - {e}")
                    skipped_count += 1

        print(f"Processed {processed_count} transactions meeting all criteria")
        print(f"Filtered out {filtered_count} transactions (date/amount/ISI serial)")
        print(f"Skipped {skipped_count} rows due to errors or incomplete data")
        
        # Save to current directory
        output_xml_path = os.path.join(os.getcwd(), 'capps_upload.xml')
        
        # Format and save XML
        xml_str = ET.tostring(root, encoding='unicode')
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="    ")
        lines = [line for line in pretty_xml.split('\n') if line.strip()]
        pretty_xml = '\n'.join(lines)
        
        with open(output_xml_path, 'w', encoding='utf-8') as xmlfile:
            xmlfile.write(pretty_xml)

        print(f"XML saved: {output_xml_path}")

        # Return the path to the generated XML file
        return output_xml_path
    
    # Keep the old method for backward compatibility
    def convert_csv_to_xml(self, csv_file_path, output_xml_path, employee_name='Store Employee'):
        """
        Legacy method for single CSV file with headers (backward compatibility)
        """
        print("Note: Using legacy single-file mode. For AIMsi exports, use two-file mode.")
        # This would contain the old implementation if needed
        # For now, just return False to indicate it should use the new method
        return False

def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(
        description='Convert AIMsi POS CSV exports to CAPPS XML format'
    )
    
    # Add subcommands for different modes
    subparsers = parser.add_subparsers(dest='mode', help='Conversion mode')
    
    # AIMsi mode (two files)
    aimsi_parser = subparsers.add_parser('aimsi', help='Convert AIMsi exports (purchases + serials)')
    aimsi_parser.add_argument(
        'purchases_file',
        help='Path to purchases CSV file from AIMsi'
    )
    aimsi_parser.add_argument(
        'serials_file',
        help='Path to serials CSV file from AIMsi (e.g., LUCASSERIALS.CSV)'
    )
    aimsi_parser.add_argument(
        '-o', '--output',
        help='Output XML file path (default: capps_upload.xml)',
        default='capps_upload.xml'
    )
    aimsi_parser.add_argument(
        '-l', '--license',
        help='Your secondhand dealer license number',
        required=True
    )
    aimsi_parser.add_argument(
        '-e', '--employee',
        help='Employee name for transactions',
        default='Store Employee'
    )
    aimsi_parser.add_argument(
        '-k', '--api-key',
        help='API key for automatic brand extraction (Groq or Gemini - both free)',
        default=None
    )
    aimsi_parser.add_argument(
        '-p', '--provider',
        help='API provider: groq or gemini (default: groq)',
        choices=['groq', 'gemini'],
        default='groq'
    )
    
    # Legacy mode (single file with headers)
    legacy_parser = subparsers.add_parser('legacy', help='Convert single CSV with headers')
    legacy_parser.add_argument(
        'csv_file',
        help='Path to CSV file with headers'
    )
    legacy_parser.add_argument(
        '-o', '--output',
        help='Output XML file path',
        default=None
    )
    legacy_parser.add_argument(
        '-l', '--license',
        help='Your secondhand dealer license number',
        required=True
    )
    legacy_parser.add_argument(
        '-e', '--employee',
        help='Employee name',
        default='Store Employee'
    )
    legacy_parser.add_argument(
        '-k', '--api-key',
        help='API key',
        default=None
    )
    legacy_parser.add_argument(
        '-p', '--provider',
        help='API provider',
        choices=['groq', 'gemini'],
        default='groq'
    )
    
    args = parser.parse_args()
    
    if not args.mode:
        parser.print_help()
        return 1
    
    # Create converter
    converter = CAPPSConverter(args.license, args.api_key, args.provider)
    
    try:
        if args.mode == 'aimsi':
            # Two-file AIMsi mode
            success = converter.convert_aimsi_to_xml(
                args.purchases_file,
                args.serials_file,
                args.output,
                args.employee
            )
        else:
            # Legacy single-file mode
            output_file = args.output or str(Path(args.csv_file).with_suffix('.xml'))
            success = converter.convert_csv_to_xml(
                args.csv_file,
                output_file,
                args.employee
            )
        
        if success:
            print(f"\nConversion complete!")
            print(f"Upload the XML file to CAPPS bulk upload system")
        else:
            print("\nConversion failed. Please check the error messages above.")
            return 1
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())