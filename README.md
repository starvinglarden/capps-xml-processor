# CAPPS XML Converter for AIMsi POS

## Overview

This tool converts CSV exports from AIMsi POS Report Wizard into CAPPS-compliant XML files for bulk upload to the California Pawn and Secondhand Dealer System.

**Key Features:**

- **FREE** AI-powered brand extraction from item descriptions
- Pattern matching fallback for 150+ common brands
- SB 1317 compliance (all customer fields set to "on file")
- GUI and command-line interfaces
- Smart caching to minimize API calls

## Brand Extraction System

The converter automatically extracts brand names from your item descriptions (e.g., "GIBSON LES PAUL STANDARD" → Brand: "GIBSON").

### Three Methods Available:

1. **Groq API (FREE - Recommended)**

   - Completely free, no credit card required
   - Uses Llama/Mixtral models
   - Fast and accurate brand detection
   - Get key at: https://console.groq.com

2. **Google Gemini API (FREE Tier)**

   - 1,500 free requests per day
   - Uses Google's Gemini Pro model
   - No credit card required for free tier
   - Get key at: https://makersuite.google.com/app/apikey

3. **Pattern Matching (No API Needed)**
   - Works offline
   - Recognizes 150+ common music store brands
   - Always available as fallback

### Getting a FREE API Key:

#### Option 1: Groq (Recommended)

1. Go to https://console.groq.com
2. Click "Sign up" (use Google or email)
3. Once logged in, go to "API Keys"
4. Create a new key
5. Copy and paste into the converter

#### Option 2: Google Gemini

1. Go to https://makersuite.google.com/app/apikey
2. Sign in with Google account
3. Click "Create API Key"
4. Copy and paste into the converter

**Both are 100% FREE - no credit card required!**

## Setup Instructions

### 1. AIMsi Report Wizard Configuration

Configure your AIMsi Report Wizard to export a CSV with these columns:

**Required Fields:**

- Transaction Date (format: YYYY-MM-DD)
- Transaction Time (format: HH:MM:SS)
- Transaction Number (unique transaction ID)
- Transaction Type (BUY, PAWN, etc.)
- Amount (transaction amount)
- Category (type of item)
- Description (full item description - brand will be extracted from this)

**Optional Fields:**

- Serial Number
- Any other custom fields

### 2. Installation

1. Ensure Python 3.6+ is installed on your computer
2. Save all converter files to a convenient location
3. (Optional) Install requests library for API support:
   ```
   pip install requests
   ```

## Usage

### GUI Version (Easiest)

1. Double-click `run_converter.bat` (Windows) or run:

   ```bash
   python capps_converter_gui.py
   ```

2. Fill in the fields:

   - **License Number**: Your CA secondhand dealer license
   - **Employee Name**: Name for transaction records
   - **OpenAI API Key**: (Optional) For AI brand extraction
   - **CSV File**: Browse to your AIMsi export
   - **Output XML**: Where to save the result

3. Click "Convert to XML"

### Command Line Usage

**Basic (with pattern matching only):**

```bash
python csv_to_capps_xml.py daily_transactions.csv -l SHD123456 -e "John Smith"
```

**With FREE Groq AI:**

```bash
python csv_to_capps_xml.py daily_transactions.csv -l SHD123456 -e "John Smith" -k "your-groq-api-key" -p groq
```

**With FREE Gemini AI:**

```bash
python csv_to_capps_xml.py daily_transactions.csv -l SHD123456 -e "John Smith" -k "your-gemini-api-key" -p gemini
```

**Parameters:**

- `-l`: Your license number (required)
- `-e`: Employee name
- `-k`: API key (optional, but FREE to get!)
- `-p`: Provider - groq or gemini (default: groq)
- `-o`: Output file name (optional)

## How Brand Extraction Works

### Input Examples:

```
"FENDER STRATOCASTER ELECTRIC GUITAR" → Brand: FENDER
"GIBSON LES PAUL STANDARD SUNBURST" → Brand: GIBSON
"BROKEN YAMAHA KEYBOARD PSR" → Brand: YAMAHA
"JAY TURSER STRAT COPY BLUE" → Brand: JAY TURSER
"ACOUSTIC GUITAR MARTIN D-28" → Brand: MARTIN
```

### Caching:

- Extracted brands are cached locally
- Same descriptions won't need re-processing
- Cache file: `~/.capps_brand_cache.json`
- Reduces API calls and speeds up processing

## Workflow Process

### Daily/Weekly Workflow:

1. **In AIMsi:**

   - Open Report Wizard
   - Create/run your transaction report
   - Include Description field (brands will be extracted)
   - Filter by date range (e.g., last 7 days)
   - Export as CSV

2. **Convert to XML:**

   - Run the converter (GUI or command line)
   - Brands are automatically extracted
   - Verify the XML file is created

3. **Upload to CAPPS:**
   - Log into CAPPS website
   - Navigate to Bulk Upload
   - Select your XML file
   - Upload transactions

## Customer Data Compliance

Per SB 1317, all customer identification fields are automatically populated with "on file":

- All personal information: "on file"
- Date of Birth: Placeholder (1900-01-01)
- Signature/Fingerprint: "on file"

**Note:** Keep actual customer data in your AIMsi system and physical records as required by law.

## CSV Format Requirements

### Essential Column: Description

The Description column should contain the full item description as it appears in AIMsi:

- Format: "BRAND MODEL DETAILS"
- Examples: "FENDER STRATOCASTER", "MARSHALL AMP", "BROKEN GIBSON LES PAUL"

### Date/Time Format

- Date: YYYY-MM-DD (e.g., 2025-01-15)
- Time: HH:MM:SS (e.g., 14:30:00)

## Troubleshooting

### Brand Extraction Issues:

**"Brand shows as UNKNOWN":**

- Check if description contains recognizable brand
- Consider adding OpenAI API key for better extraction
- Manually edit the brand cache file if needed

**"API errors":**

- Verify your OpenAI API key is correct
- Check internet connection
- Fallback to pattern matching will activate automatically

**"Requests library not found":**

- Install it: `pip install requests`
- Or continue without it (pattern matching only)

### Common Issues:

**CSV reading errors:**

- Ensure CSV has proper headers
- Check for special characters
- Save as UTF-8 encoding

**XML validation errors in CAPPS:**

- Verify all required fields are present
- Check date formats
- Ensure transaction numbers are unique

## Why Use the API?

**Benefits of FREE API:**

- Much more accurate than pattern matching
- Handles tricky cases like "BROKEN GIBSON" or "JAY TURSER STRAT COPY"
- Completely FREE (no hidden costs)
- Fast (under 1 second per item)
- Works great on older computers (processing done in cloud)

**Pattern Matching Still Works:**

- If you prefer not to sign up for anything
- Internet connection issues
- Already recognizes 150+ common brands

## Cost Comparison

| Method           | Cost                 | Accuracy  | Setup Time |
| ---------------- | -------------------- | --------- | ---------- |
| Groq API         | **FREE**             | Excellent | 2 minutes  |
| Gemini API       | **FREE** (1,500/day) | Excellent | 2 minutes  |
| Pattern Matching | **FREE**             | Good      | None       |

## Advanced Configuration

### Editing the Brand Cache

The cache file (`~/.capps_brand_cache.json`) can be manually edited:

```json
{
  "GIBSON LES PAUL STANDARD": "GIBSON",
  "FENDER STRATOCASTER": "FENDER",
  "CUSTOM SHOP GUITAR": "CUSTOM SHOP"
}
```

### Adding Custom Brands

Edit the `KNOWN_BRANDS` list in `csv_to_capps_xml.py` to add brands specific to your inventory.

## Support & Compliance

## Support & Links

**CAPPS Support:**

- Email: CAPSS@doj.ca.gov
- Website: https://oag.ca.gov/secondhand/capss

**FREE API Providers:**

- Groq: https://console.groq.com (Recommended - completely free)
- Google Gemini: https://makersuite.google.com/app/apikey (1,500 free/day)

## Version History

- v2.0 (2025-01): Added AI-powered brand extraction
  - OpenAI API integration
  - Pattern matching fallback
  - Brand caching system
  - Improved GUI with API key field
- v1.0 (2025-01): Initial release
  - SB 1317 compliance
  - Basic CSV to XML conversion

---

For questions about the converter, check the error messages and this documentation first. For CAPPS-specific questions, contact CAPSS@doj.ca.gov.
