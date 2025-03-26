import requests
from bs4 import BeautifulSoup
import re
import logging
from urllib.parse import urlparse
import hashlib

logger = logging.getLogger(__name__)

class PricechartingService:
    """Service for interacting with pricecharting.com."""
    
    @staticmethod
    def is_valid_pricecharting_url(url):
        """
        Check if a URL is a valid pricecharting.com URL.
        
        Args:
            url (str): URL to check
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not url:
            return False
            
        # Check if it's a string
        if not isinstance(url, str):
            return False
            
        # Check if it starts with the pricecharting domain
        if not url.startswith('https://www.pricecharting.com/game/'):
            return False
            
        # Parse the URL
        parsed_url = urlparse(url)
        
        # Check domain
        if parsed_url.netloc != 'www.pricecharting.com':
            return False
            
        # Check path structure (should be /game/console/game-name)
        path_parts = parsed_url.path.split('/')
        if len(path_parts) < 4 or path_parts[1] != 'game':
            return False
            
        return True
    
    @staticmethod
    def clean_game_name(original):
        """Clean game name for URL construction."""
        return original.lower().strip().replace(':', '').replace('.', '').replace("'", '%27').replace(' ', '-').replace('--', '-').replace('--', '-').replace('(', '').replace(')', '').replace('[', '').replace(']', '').replace('/', '').replace('#', '').strip()
    
    @staticmethod
    def clean_system_name(original):
        """Clean system name for URL construction."""
        return original.lower().replace('new', '').strip().replace(' ', '-')
    
    @staticmethod
    def extract_id(document):
        """Extract game ID from the product name element."""
        element = document.select_one('#product_name')
        if element and element.get('title'):
            text = element.get('title').strip()
            return text.replace(',', '')
        return None
    
    @staticmethod
    def extract_game_data_from_url(url):
        """
        Extract game data from a pricecharting.com URL.
        
        Args:
            url (str): URL to extract data from
            
        Returns:
            dict: Game data including name, console, pricecharting_id, and URL
            
        Raises:
            ValueError: If the URL is invalid or data couldn't be extracted
        """
        # Validate URL
        if not PricechartingService.is_valid_pricecharting_url(url):
            raise ValueError(f"Invalid pricecharting.com URL: {url}")
            
        # Fetch the page
        try:
            logger.info(f"Fetching page: {url}")
            response = requests.get(url)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching page: {e}")
            raise ValueError(f"Failed to fetch page: {str(e)}")
            
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract game name using the repository method
        pricecharting_id = PricechartingService.extract_id(soup)
        
        # If ID extraction failed, try fallback methods
        if not pricecharting_id:
            # Extract title for fallback methods
            title_tag = soup.find('title')
            title_text = title_tag.text if title_tag else ""
            
            # Try JavaScript extraction (fallback 1)
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'product_id' in script.string:
                    match = re.search(r'product_id\s*[:=]\s*[\'"]?(\d+)[\'"]?', script.string)
                    if match:
                        pricecharting_id = match.group(1)
                        break
            
            # Try data attributes (fallback 2)
            if not pricecharting_id:
                elements_with_data = soup.select('[data-product-id]')
                if elements_with_data:
                    pricecharting_id = elements_with_data[0]['data-product-id']
            
            # Try JSON patterns (fallback 3)
            if not pricecharting_id:
                html_str = str(soup)
                json_pattern = re.search(r'"id"\s*:\s*"([^"]+)"', html_str)
                if json_pattern:
                    pricecharting_id = json_pattern.group(1)
            
            # Generate from URL hash if all else fails
            if not pricecharting_id:
                logger.warning(f"Could not find pricecharting_id for {url}, generating a fallback ID")
                url_hash = hashlib.md5(url.encode()).hexdigest()
                pricecharting_id = url_hash[:9]  # Use first 9 chars of hash
        
        # Extract game name
        name = None
        
        # Try from product_name element first
        product_name = soup.select_one('#product_name')
        if product_name:
            name = product_name.text.strip()
        
        # If not found, try title
        if not name:
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.text
                name = title_text.split('|')[0].strip() if '|' in title_text else title_text.strip()
                if "Price Guide" in name:
                    name = name.replace("Price Guide", "").strip()
        
        # Extract console from URL path
        path_parts = urlparse(url).path.split('/')
        try:
            console = path_parts[2] if len(path_parts) > 2 else "unknown"
            # Normalize console name
            console = console.replace('-', ' ').title()
        except:
            console = "unknown"
            
        # Remove console name from the game title if it appears at the end
        if name and console != "unknown":
            # Check if the console name appears at the end of the game title
            if name.endswith(console):
                name = name[:-len(console)].strip()
            # Also try with "Nintendo" prefix for Nintendo consoles
            elif console.startswith("Nintendo") and name.endswith(console.replace("Nintendo ", "")):
                name = name[:-len(console.replace("Nintendo ", ""))].strip()
            # Also check if the console name appears anywhere in the title
            elif console in name:
                name = name.replace(console, "").strip()
        
        # Clean up any extra spaces or punctuation at the end
        name = name.rstrip(' -:,')
        
        result = {
            'name': name,
            'console': console,
            'pricecharting_id': pricecharting_id,
            'url': url
        }
        
        logger.info(f"Extracted game data: {result}")
        return result
