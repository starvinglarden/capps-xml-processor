# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a specialized data conversion tool for music stores using AIMsi POS software. It converts CSV transaction exports from AIMsi into CAPPS-compliant XML format for bulk upload to California's Pawn and Secondhand Dealer System.

**Key Purpose:** Help music stores comply with California SB 1317 reporting requirements by automating the conversion of their POS transaction data into the exact XML format required by CAPPS.

## Running the Application

### GUI Version (Primary Interface)
```bash
# Windows
run_converter.bat

# Cross-platform
python capps_converter_gui.py
```

### Command Line (Two-File AIMsi Mode)
```bash
python csv_to_capps_xml.py aimsi \
  purchases.csv \
  LUCASSERIALS.CSV \
  -l LICENSE_NUMBER \
  -e "Employee Name" \
  -k API_KEY \
  -p groq
```

**Parameters:**
- `-l/--license`: CA secondhand dealer license number (required)
- `-e/--employee`: Employee name for transaction records
- `-k/--api-key`: Optional API key for brand extraction (Groq or Gemini)
- `-p/--provider`: API provider - "groq" or "gemini" (default: groq)
- `-o/--output`: Output XML file path (default: capps_upload.xml)

### Python Environment
```bash
# Activate virtual environment if exists
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Unix

# Install dependencies
pip install requests
```

## Architecture

### Two-File Processing Model

The converter uses a **dual-file architecture** specific to AIMsi POS exports:

1. **Purchases CSV** (no headers): Contains transaction summary data
   - Columns: DateTime, Transaction#, Amount, CategoryID, SerialNumber
   - One row per transaction item

2. **Serials CSV** (with headers): Contains detailed item information
   - Used as lookup table: SerialNumber → (Description, Subcategory)
   - This is where actual item descriptions live

**Why Two Files?** AIMsi's export structure separates transaction metadata from item details. The converter joins these datasets using serial numbers as the key, similar to a SQL JOIN operation.

### Core Components

**`CAPPSConverter` (csv_to_capps_xml.py:303-818)**
- Main conversion orchestrator
- Handles XML structure generation (lines 511-517)
- Maps AIMsi category codes to CAPPS article types via nested dictionaries (lines 316-435)
- Processes purchase transactions and enforces 7-day filter (lines 567-672)
- Integrates with CAPPS API for direct upload (lines 674-739)

**`BrandExtractor` (csv_to_capps_xml.py:33-301)**
- Extracts brand names from item descriptions
- Three-tier extraction strategy:
  1. Cache lookup (fastest)
  2. AI API (Groq/Gemini - optional but accurate)
  3. Pattern matching against 150+ known musical instrument brands (fallback)
- Persistent cache in `~/.capps_brand_cache.json`

**`CAPPSConverterGUI` (capps_converter_gui.py:21-567)**
- Tkinter GUI wrapper around CAPPSConverter
- Auto-saves all settings to `~/.capps_converter_settings.json` via variable traces
- Settings persist across sessions

### Critical Business Logic

**Date Filtering (csv_to_capps_xml.py:600-615)**
- Only processes transactions from last 5 days (hardcoded as 7-day filter with 5-day limit)
- Rejects future-dated transactions
- This prevents accidental duplicate uploads of old data

**SB 1317 Compliance (csv_to_capps_xml.py:519-565)**
- ALL customer PII fields must be set to "on file"
- DOB field uses xsi:nil="true" with text override
- This is legally required - stores keep actual customer data in AIMsi/physical records

**Category Mapping (csv_to_capps_xml.py:316-435)**
- Nested dictionary: `category_map[category_id][subcategory_id] → CAPPS article type`
- Maps AIMsi's proprietary category system to CAPPS's standardized types
- Example: `category_map['3']['1']` = "GUITAR" (Guitars/Fretted → Acoustics)

**Brand Extraction Fallback Chain:**
```
Description → Cache hit? → Return cached
           ↓ no
           → API available? → Call Groq/Gemini → Cache & return
           ↓ no
           → Pattern match → Cache & return
```

### Data Flow

```
AIMsi Purchases CSV + Serials CSV
        ↓
    CAPPSConverter.convert_aimsi_to_xml()
        ↓
    Load serials_data dict (serial → description/subcategory)
        ↓
    For each purchase row:
        - Parse datetime (AIMsi format: "MM/DD/YYYY HH:MM:SS AM/PM")
        - Check 7-day filter
        - Lookup serial in serials_data
        - Extract brand from description
        - Map category → CAPPS article type
        - Build XML <item> element
        ↓
    Generate XML with minidom pretty-print
        ↓
    Save to capps_upload.xml
        ↓
    Optional: Upload to CAPPS API
```

## Key Implementation Details

### DateTime Parsing
AIMsi format: `"11/10/2025 11:50:05 AM"`
CAPPS format: `"2025-11-10T11:50:05"`

Conversion happens in `parse_aimsi_datetime()` (csv_to_capps_xml.py:451-464)

### Color Extraction
The `get_color()` method (csv_to_capps_xml.py:466-474) normalizes color descriptions:
- Maps common musical instrument finishes → base colors
- Examples: "SUNBURST" → "BROWN", "WINE" → "RED"
- Falls back to "Other" if no color found

### API Integration
Supports two FREE APIs for brand extraction:
- **Groq** (default): Uses llama-3.1-8b-instant model
- **Gemini**: Uses Google's gemini-pro model

Both use low temperature (0.1) and short max_tokens (20) for consistent, terse responses.

### XML Structure
CAPPS requires specific XML schema:
```xml
<capssUpload xmlns:xsi="...">
  <bulkUploadData licenseNumber="...">
    <propertyTransaction>
      <transactionTime>2025-01-15T14:30:00</transactionTime>
      <customer><!-- All fields = "on file" --></customer>
      <store><employeeName>...</employeeName></store>
      <items>
        <item>
          <type>BUY</type>
          <article>GUITAR</article>
          <brand>FENDER</brand>
          <!-- etc -->
        </item>
      </items>
    </propertyTransaction>
  </bulkUploadData>
</capssUpload>
```

## Common Modification Scenarios

### Adding New Brand Patterns
Edit `BrandExtractor.KNOWN_BRANDS` list (csv_to_capps_xml.py:37-69)

### Adding New Category Mappings
Update `self.category_map` dictionary in `CAPPSConverter.__init__()` (csv_to_capps_xml.py:316-435)

### Changing Date Filter
Modify the hardcoded `5` in line 605:
```python
if days_ago > 5:  # Change this number
```

### Adding GUI Fields
1. Add StringVar in `CAPPSConverterGUI.__init__()` (capps_converter_gui.py:28-37)
2. Add trace in `setup_auto_save()` (capps_converter_gui.py:48-59)
3. Add widget in `create_widgets()` (capps_converter_gui.py:61-352)
4. Add to settings save/load (capps_converter_gui.py:501-566)

## Error Handling Patterns

The codebase uses forgiving error handling appropriate for a user-facing desktop app:

- **Silent failures**: Cache operations (save/load) fail silently
- **User-friendly messages**: GUI shows messagebox dialogs for validation errors
- **Graceful degradation**: If API fails, falls back to pattern matching
- **Informative logging**: Prints row-by-row processing status to console

## Dependencies

**Required:**
- Python 3.6+
- Standard library: csv, xml, datetime, argparse, json, re, ssl, pathlib, os

**Optional:**
- `requests` - Only needed for API brand extraction and CAPPS upload
- `tkinter` - Usually bundled with Python, needed for GUI

## Important Notes

- **No tests exist** - This is a simple utility script without a test suite
- **No git repo** - Project is not currently version controlled
- **Settings persistence**: Both GUI settings and brand cache use JSON files in user's home directory
- **Windows-focused**: Batch file launcher is Windows-specific, but Python code is cross-platform
- **Security**: CAPPS API upload uses TLS 1.2 via custom adapter (csv_to_capps_xml.py:23-31)
- **Hardcoded values**: Transaction type always "BUY", many item fields default to "Unknown" or "None"
