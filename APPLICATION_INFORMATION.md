# Game Collection Manager - Application Information

## Overview
The Game Collection Manager is a Flask-based web application designed for managing personal video game collections. It provides comprehensive functionality for tracking games across their lifecycle: from wishlist → purchased → for sale/lent → removed, with full price tracking and collection analytics.

## Application Architecture

### Technology Stack
- **Backend**: Flask (Python WSGI application)
- **Database**: SQLite (`games.db`)
- **Frontend**: Bootstrap 5, vanilla JavaScript, ApexCharts
- **Entry Point**: `wsgi.py` (not `app.py` due to naming conflicts)
- **Deployment**: Gunicorn with systemd service, Ubuntu server for local network access
- **Dependencies**: Listed in `requirements.txt` including Flask, boto3, requests, lxml

### Authentication Status
- **NO AUTHENTICATION REQUIRED** - Auth0 integration has been completely removed
- Application runs locally on VPN/private network only
- All routes are publicly accessible without login

## Database Schema (`games.db`)

### Core Tables

#### `physical_games`
Primary game registry table:
```sql
- id (INTEGER PRIMARY KEY AUTOINCREMENT)
- name (TEXT NOT NULL)
- console (TEXT NOT NULL)
```

#### `wanted_games` (Wishlist)
```sql
- id (INTEGER PRIMARY KEY AUTOINCREMENT)
- physical_game (INTEGER, FK to physical_games.id)
- condition (TEXT DEFAULT 'complete')
```

#### `purchased_games` (Collection)
```sql
- id (INTEGER PRIMARY KEY AUTOINCREMENT)
- physical_game (INTEGER, FK to physical_games.id)
- acquisition_date (DATE NOT NULL)
- source (TEXT)
- price (DECIMAL)
- condition (TEXT)
```

#### `games_for_sale`
```sql
- id (INTEGER PRIMARY KEY AUTOINCREMENT)
- purchased_game_id (INTEGER, FK to purchased_games.id)
- date_marked (DATE DEFAULT now())
- asking_price (DECIMAL)
- notes (TEXT)
- original_acquisition_date (DATE) -- Denormalized for history
- original_source (TEXT)
- original_purchase_price (DECIMAL)
```

#### `lent_games`
```sql
- id (INTEGER PRIMARY KEY AUTOINCREMENT)
- purchased_game (INTEGER, FK to purchased_games.id)
- lent_date (DATE NOT NULL)
- lent_to (TEXT NOT NULL)
- note (TEXT)
- returned_date (DATE NULL)
```

### Price Tracking Tables

#### `pricecharting_games`
```sql
- id (INTEGER PRIMARY KEY AUTOINCREMENT)
- pricecharting_id (INTEGER)
- name (TEXT NOT NULL)
- console (TEXT NOT NULL)
- url (TEXT)
```

#### `pricecharting_prices`
```sql
- id (INTEGER PRIMARY KEY AUTOINCREMENT)
- retrieve_time (TIMESTAMP)
- pricecharting_id (INTEGER, FK)
- new (DECIMAL)
- loose (DECIMAL)
- complete (DECIMAL)
- condition (TEXT)
- price (DECIMAL)
```

#### `physical_games_pricecharting_games`
Junction table linking physical games to pricecharting data:
```sql
- id (INTEGER PRIMARY KEY AUTOINCREMENT)
- physical_game (INTEGER, FK)
- pricecharting_game (INTEGER, FK)
```

## API Endpoints

### Collection Management
- `GET /api/collection` - Get paginated collection with totals
  - Returns: `{"games": [...], "totals": {"total_acquisition_price": X, "total_current_price": Y}}`
  - Supports sorting, pagination, filtering
- `POST /api/collection/add` - Add game to collection from PriceCharting URL
- `DELETE /api/game/<id>/remove_from_collection` - Remove game entirely from collection

### Wishlist Management  
- `POST /api/wishlist/add` - Add game to wishlist from PriceCharting URL
- `DELETE /api/wishlist/<id>/remove` - Remove game from wishlist
- `POST /api/wishlist/<id>/purchase` - Convert wishlist item to purchased

### Game State Management
- `POST /api/game/<id>/mark_for_sale` - Mark owned game for sale
- `DELETE /api/game/<id>/unmark_for_sale` - Remove from sale
- `POST /api/game/<id>/mark_as_lent` - Mark game as lent out
- `DELETE /api/game/<id>/unmark_as_lent` - Return game from lent

### Game Information Updates
- `PUT /api/game/<id>/details` - Update game name and console
- `PUT /api/game/<id>/condition` - Update game condition
- `PUT /api/wishlist/<id>/condition` - Update wishlist item condition

### Price Operations
- `POST /api/game/<id>/update_price` - Scrape and update current prices
- `GET /api/game/<id>/last_price_update` - Get last price update timestamp
- `GET /api/game/<id>/price_history` - Get historical price data for charting

## User Interface Features

### Main Collection View
- **Responsive Table Layout**: Desktop shows all columns, mobile shows condensed cards
- **Multi-Column Sorting**: Click column headers, visual sort indicators (↑↓)
- **Advanced Filtering**:
  - Text search (searches name, console, source)
  - Multi-checkbox console selection with "All Consoles" master control
  - Status filter (All, Owned, For Sale, Lent Out, Wishlist)
  - Condition filter (All conditions, Complete, Good, etc.)
- **Pagination**: 30 items per page with Bootstrap pagination controls
- **Collection Totals**: Shows total acquisition cost vs current market value

### Game Cards (Expandable Details)
Each game displays contextual information and actions based on its state:

#### Core Information Display
- Game name, console, condition
- Purchase info (date, source, price) if owned
- Current market price with value change indicator
- Sale status with asking price/notes if marked for sale
- Lent status with person and date if lent out
- Price history sparkline chart
- Last price update timestamp

#### Context-Sensitive Action Buttons
**Wishlist Items:**
- 📦 Purchase (convert to collection)
- ✏️ Edit Condition
- 🗑️ Remove from Wishlist

**Owned Games:**
- 💰 Mark for Sale / 🔄 Unmark for Sale
- 📤 Mark as Lent / 🔙 Return from Lent
- ✏️ Edit Condition
- 🗑️ Remove from Collection
- 🔄 Update Price

**All Games:**
- ✏️ Edit Details (name/console)
- 📊 Price History (sparkline chart)

### Professional Modal Dialogs
All major actions use Bootstrap modals instead of browser confirms:

#### Add Game Modal
- **Tabbed Interface**: Wishlist vs Collection tabs
- **PriceCharting Integration**: Paste URL to auto-populate name/console
- **Conditional Fields**: Purchase fields only shown for collection tab
- **Form Validation**: Required field validation
- **Batch Support**: Modal stays open after successful adds for multiple entries

#### Other Modals
- **Purchase Modal**: Convert wishlist to collection (date, source, price)
- **Edit Details Modal**: Change game name and console
- **Condition Modal**: Update game condition with dropdown
- **Mark for Sale Modal**: Set asking price and notes
- **Lent Out Modal**: Record lent date and person
- **Confirmation Modals**: Professional warnings for destructive actions

## Advanced Features

### Price Tracking System
- **Web Scraping**: Automated price retrieval from PriceCharting.com
- **Historical Data**: Tracks price changes over time
- **Visual Charts**: ApexCharts sparklines showing price trends
- **Manual Updates**: One-click price refresh per game
- **Value Analytics**: Shows gain/loss compared to purchase price

### Multi-Console Filtering
- **OR Logic**: Select multiple consoles simultaneously
- **Master Control**: "All Consoles" checkbox toggles all others
- **Smart Interaction**: Individual selections auto-uncheck "All Consoles"
- **Real-time Filtering**: Instant results without page refresh
- **Scrollable Interface**: Handles large console lists gracefully

### Collection Analytics
- **Financial Overview**: Total acquisition cost vs current market value
- **Dynamic Totals**: Recalculates for filtered results
- **Per-Game Analytics**: Individual gain/loss calculations
- **Export Capability**: S3 backup system for data portability

### Mobile-First Design
- **Progressive Web App**: PWA manifest with app icons
- **Responsive Layout**: Adaptive table/card layouts
- **Touch-Friendly**: Large buttons and touch targets
- **Offline-Ready**: Service worker support for caching

## Data Management

### Import/Export System
- **PriceCharting Integration**: Add games via URL parsing
- **S3 Backup System**: Automated database backups every 6 hours
- **Historical Backups**: Timestamped backup retention
- **AWS Integration**: Uses same S3 bucket as CLI tools

### Data Integrity
- **Foreign Key Constraints**: Proper relational integrity
- **Transaction Safety**: Database operations in transactions
- **Validation**: Client and server-side input validation
- **Error Handling**: Comprehensive error recovery

## Deployment Configuration

### Local Development
```bash
cd /path/to/collecting-website
source venv/bin/activate
python wsgi.py  # Runs on http://localhost:8080
```

### Production Deployment
- **Ubuntu Server**: Systemd service with Gunicorn
- **Local Network Only**: No internet exposure, VPN/private access
- **Automated Deployment**: GitHub Actions with self-hosted runner
- **Service Management**: `collecting-website.service` systemd unit
- **Log Management**: Application and backup logging
- **Firewall Configuration**: UFW rules for local network access

### Backup System
- **Automated S3 Uploads**: Every 6 hours via cron job
- **Manual Backup**: `sudo -u www-data python3 backup_to_s3.py`
- **Log Monitoring**: `/var/log/collecting-website-backup.log`
- **AWS Credentials**: Configured for www-data user

## Game Lifecycle Management

### Complete Workflow Support
1. **Discovery**: Add games to wishlist from PriceCharting URLs
2. **Acquisition**: Convert wishlist items to collection with purchase details
3. **Ownership**: Track condition, update prices, view analytics
4. **Lending**: Mark games as lent out with tracking
5. **Sale**: Mark for sale with asking prices and notes
6. **Removal**: Complete removal with data cleanup

### State Transitions
- Wishlist → Collection (Purchase)
- Collection → For Sale (Mark for Sale)
- Collection → Lent Out (Mark as Lent)
- Any State → Removed (Delete)
- For Sale → Collection (Unmark for Sale)
- Lent Out → Collection (Return from Lent)

## Performance Characteristics

### Scalability
- **SQLite Database**: Suitable for personal collections (tested with 1000+ games)
- **Pagination**: 30 items per page prevents large data loads
- **Lazy Loading**: Price charts loaded on demand
- **Client-Side Filtering**: Fast search and filter operations

### Optimization
- **Database Indexes**: Proper indexing on foreign keys and search fields
- **Query Optimization**: Efficient JOINs with latest price data
- **Caching Strategy**: Static assets cached, dynamic data fresh
- **Minimal Dependencies**: Lightweight JavaScript, no heavy frameworks

This application provides a complete, professional-grade solution for video game collection management with modern web technologies and comprehensive functionality covering the entire game ownership lifecycle.
