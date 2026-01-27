import urllib.request
import urllib.parse
import time
from typing import Optional, Dict

class MacVendorLookup:
    """
    Utility to look up MAC address vendors using api.macvendors.com.
    Includes simple caching to avoid hitting rate limits.
    """
    
    BASE_URL = "https://api.macvendors.com/"
    _cache: Dict[str, str] = {}
    _last_request_time = 0
    
    @staticmethod
    def lookup(mac_address: str) -> str:
        """
        Looks up the vendor for a given MAC address.
        
        Args:
            mac_address: The MAC address string (e.g., "FC:FB:FB:01:FA:21")
            
        Returns:
            The vendor name or "Unknown Vendor" if not found/error.
        """
        if not mac_address:
            return "Unknown"
            
        # Clean MAC address for key (top 3 octets are OUI)
        clean_mac = mac_address.replace("-", ":").upper()
        
        # Check cache first
        if clean_mac in MacVendorLookup._cache:
            return MacVendorLookup._cache[clean_mac]
            
        # Rate limiting: The API is free but sensitive. Sleep if needed.
        # We'll stick to ~1 request per second to be safe.
        now = time.time()
        if now - MacVendorLookup._last_request_time < 1.1:
            time.sleep(1.1 - (now - MacVendorLookup._last_request_time))
            
        try:
            url = MacVendorLookup.BASE_URL + urllib.parse.quote(clean_mac)
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'IRIS-Incident-Response-Tool/1.0'}
            )
            
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    vendor = response.read().decode('utf-8').strip()
                    MacVendorLookup._cache[clean_mac] = vendor
                    MacVendorLookup._last_request_time = time.time()
                    return vendor
                    
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return "Vendor Not Found"
            if e.code == 429:
                return "Rate Limit Exceeded"
        except Exception:
            pass
            
        MacVendorLookup._last_request_time = time.time()
        return "Unknown Vendor"

# Simple test if run directly
if __name__ == "__main__":
    print(MacVendorLookup.lookup("FC:FB:FB:01:FA:21"))
