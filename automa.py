
import base64
import logging
import random
import requests
from typing import Optional, Tuple
from seleniumbase import SB

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GeolocationManager:
    """Manages geolocation data retrieval and storage."""
    
    @staticmethod
    def fetch_geo_data() -> dict:
        """
        Fetch geolocation data from IP API.
        
        Returns:
            Dictionary containing lat, lon, timezone, and countryCode
        """
        try:
            logger.info("Fetching geolocation data...")
            response = requests.get("http://ip-api.com/json/")
            response.raise_for_status()
            geo_data = response.json()
            logger.info(f"Location: {geo_data.get('city')}, {geo_data.get('country')}")
            return geo_data
        except requests.RequestException as e:
            logger.error(f"Failed to fetch geolocation: {e}")
            raise
    
    @staticmethod
    def extract_location(geo_data: dict) -> Tuple[float, float, str]:
        """
        Extract location coordinates and timezone.
        
        Args:
            geo_data: Geolocation dictionary
            
        Returns:
            Tuple of (latitude, longitude, timezone_id)
        """
        return (
            geo_data["lat"],
            geo_data["lon"],
            geo_data["timezone"]
        )


class ChannelDecoder:
    """Handles base64 decoding of channel names."""
    
    @staticmethod
    def decode_channel(encoded_name: str) -> str:
        """
        Decode base64 encoded channel name.
        
        Args:
            encoded_name: Base64 encoded channel name
            
        Returns:
            Decoded channel name
        """
        try:
            decoded = base64.b64decode(encoded_name).decode("utf-8")
            logger.info(f"Decoded channel: {decoded}")
            return decoded
        except Exception as e:
            logger.error(f"Failed to decode channel name: {e}")
            raise
    
    @staticmethod
    def build_url(channel_name: str, platform: str = "twitch") -> str:
        """
        Build platform URL from channel name.
        
        Args:
            channel_name: Channel name
            platform: "twitch" or "youtube"
            
        Returns:
            Full URL
        """
        if platform == "twitch":
            url = f"https://www.twitch.tv/{channel_name}"
        elif platform == "youtube":
            url = f"https://www.youtube.com/@{channel_name}/live"
        else:
            raise ValueError(f"Unknown platform: {platform}")
        
        logger.info(f"Target URL: {url}")
        return url


class StreamViewer:
    """Handles browser automation for stream viewing."""
    
    BROWSER_CONFIG = {
        'uc': True,
        'locale': 'en',
        'ad_block': True,
        'chromium_arg': '--disable-webgl',
    }
    
    WATCH_TIME_RANGE = (450, 800)  # seconds
    
    def __init__(self, url: str, latitude: float, longitude: float, timezone: str):
        """
        Initialize stream viewer.
        
        Args:
            url: Stream URL
            latitude: Viewer latitude
            longitude: Viewer longitude
            timezone: Viewer timezone
        """
        self.url = url
        self.latitude = latitude
        self.longitude = longitude
        self.timezone = timezone
    
    def run(self) -> None:
        """Execute the main viewing loop with multiple viewers."""
        while True:
            try:
                with SB(**self.BROWSER_CONFIG, proxy=False) as driver:
                    logger.info("Primary viewer session started")
                    
                    self._activate_and_setup(driver, self.url)
                    
                    # Check if stream is live
                    if not driver.is_element_present("#live-channel-stream-information"):
                        logger.warning("Stream not live, exiting")
                        break
                    
                    logger.info("Stream is live, starting secondary viewers")
                    
                    # Accept any remaining prompts
                    self._accept_prompt(driver)
                    
                    # Start secondary viewer
                    self._start_secondary_viewer(driver)
                    
                    # Watch for random duration
                    watch_time = random.randint(*self.WATCH_TIME_RANGE)
                    logger.info(f"Watching for {watch_time}s")
                    driver.sleep(watch_time)
            except KeyboardInterrupt:
                logger.info("Automation interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error in viewing session: {e}", exc_info=True)
                break
        
    def _activate_and_setup(self, driver, url: str) -> None:
        """
        Activate CDP mode and handle initial prompts.
        
        Args:
            driver: SeleniumBase driver
            url: Stream URL
        """
        logger.info("Activating CDP mode with geolocation...")
        driver.activate_cdp_mode(
            url,
            tzone=self.timezone,
            geoloc=(self.latitude, self.longitude)
        )
        driver.sleep(2)
        
        # Accept initial prompts
        self._accept_prompt(driver)
        driver.sleep(2)
        
        # Click "Start Watching" if present
        if driver.is_element_present('button:contains("Start Watching")'):
            logger.info("Clicking 'Start Watching'")
            driver.cdp.click('button:contains("Start Watching")', timeout=4)
            driver.sleep(10)
        
        # Accept any additional prompts
        self._accept_prompt(driver)
        driver.sleep(2)
    
    def _accept_prompt(self, driver) -> None:
        """
        Accept "Accept" button if present.
        
        Args:
            driver: SeleniumBase driver
        """
        if driver.is_element_present('button:contains("Accept")'):
            logger.info("Accepting prompt")
            driver.cdp.click('button:contains("Accept")', timeout=4)
    
    def _start_secondary_viewer(self, driver) -> None:
        """
        Start a secondary viewer in a new driver.
        
        Args:
            driver: Primary SeleniumBase driver
        """
        try:
            logger.info("Starting secondary viewer")
            secondary_driver = driver.get_new_driver(undetectable=True)
            
            self._activate_and_setup(secondary_driver, self.url)
            
            driver.sleep(10)
            logger.info("Secondary viewer initialized")
        except Exception as e:
            logger.error(f"Error starting secondary viewer: {e}")


def main() -> None:
    """Entry point for the stream viewer automation."""
    try:
        # Fetch geolocation
        geo_data = GeolocationManager.fetch_geo_data()
        latitude, longitude, timezone = GeolocationManager.extract_location(geo_data)
        
        # Decode channel and build URL
        encoded_channel = "YnJ1dGFsbGVz"  # "brutallyes" in base64
        decoder = ChannelDecoder()
        channel_name = decoder.decode_channel(encoded_channel)
        #channel_name = "topson"
        url = decoder.build_url(channel_name, platform="twitch")
        
        # Start viewing
        viewer = StreamViewer(url, latitude, longitude, timezone)
        viewer.run()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()
