import json
import logging
import re
import asyncio
from typing import List, Dict, Optional
import aiohttp
from bs4 import BeautifulSoup
from .config import TIKTOK_HEADERS
from .downloader import check_redirect

logger = logging.getLogger(__name__)

def extract_audio_urls_from_video_tags(video_tags: str) -> List[str]:
    """Extract video URLs from video tags."""
    logger.info("Extracting video URLs from video tags")
    
    # Log the video tag content for debugging
    logger.debug(f"Video tag content: {video_tags}")
    
    # Look for video URLs in the video tags
    video_urls = []
    
    # Try to find all video tags in the HTML
    video_tag_pattern = r'<video[^>]*>.*?</video>'
    video_tags_list = re.findall(video_tag_pattern, video_tags, re.DOTALL)
    logger.debug(f"Found {len(video_tags_list)} video tags in HTML")
    
    for tag in video_tags_list:
        # Look for src attribute
        src_match = re.search(r'src="([^"]+)"', tag)
        if src_match:
            video_url = src_match.group(1)
            # Clean up the URL (remove HTML entities)
            video_url = video_url.replace('&amp;', '&')
            video_urls.append(video_url)
            logger.debug(f"Found video URL: {video_url}")
    
    if not video_urls:
        logger.warning("No video URLs found in video tags")
        return []
    
    logger.info(f"Found {len(video_urls)} video URLs")
    return video_urls

async def extract_video_tags_from_embed(embed_url: str, session: aiohttp.ClientSession) -> Optional[str]:
    """Extract video tags from TikTok embed page."""
    try:
        logger.info(f"Fetching TikTok embed page: {embed_url}")
        # Use a shorter timeout for the embed page request
        timeout = aiohttp.ClientTimeout(total=10)
        async with session.get(embed_url, headers=TIKTOK_HEADERS, timeout=timeout) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find all video tags
                video_tags = soup.find_all('video')
                logger.debug(f"Found {len(video_tags)} video tags in embed page")
                
                if video_tags:
                    # Log the attributes of each video tag for debugging
                    for i, tag in enumerate(video_tags):
                        logger.debug(f"Video tag {i + 1} attributes: {tag.attrs}")
                    
                    # Return the outer HTML of all video tags
                    return ''.join(str(tag) for tag in video_tags)
                else:
                    logger.warning("No video tags found in embed page")
                    return None
            else:
                logger.error(f"Failed to fetch embed page: HTTP {response.status}")
                return None
    except Exception as e:
        logger.error(f"Error extracting video tags: {str(e)}")
        return None

def load_tiktok_data(file_path: str) -> List[Dict]:
    """Load TikTok data from JSON file."""
    try:
        logger.info(f"Loading TikTok data from {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Check if this is a TikTok data export
        if isinstance(data, dict):
            # Get the Favorite Sounds list
            favorite_sounds = data.get("Your Activity", {}).get("Favorite Sounds", {}).get("FavoriteSoundList", [])
            if favorite_sounds:
                logger.info(f"Found {len(favorite_sounds)} favorite sounds")
                return favorite_sounds
            else:
                logger.warning("No favorite sounds found in the data")
                return []
        else:
            logger.warning("Unexpected data format")
            return []
            
    except Exception as e:
        logger.error(f"Error loading TikTok data: {str(e)}")
        return []

def extract_sound_links(data: List[Dict]) -> List[str]:
    """Extract sound links from TikTok data."""
    sound_links = []
    for entry in data:
        # Log the structure of each entry for debugging
        logger.debug(f"Processing entry: {json.dumps(entry, indent=2)}")
        
        # Check for different possible structures in favorite sounds
        if isinstance(entry, dict):
            # Try different possible field names for the sound URL
            for field in ["PlayURL", "PlayUrl", "playUrl", "play_url", "url", "Link", "link"]:
                if field in entry:
                    sound_links.append(entry[field])
                    break
            
            # Also check for nested sound information
            sound_info = entry.get("Sound", {})
            if sound_info:
                for field in ["PlayURL", "PlayUrl", "playUrl", "play_url", "url", "Link", "link"]:
                    if field in sound_info:
                        sound_links.append(sound_info[field])
                        break
    
    logger.info(f"Extracted {len(sound_links)} sound links from favorite sounds")
    if len(sound_links) == 0:
        logger.warning("No sound links found. Data structure might be different than expected.")
    return sound_links

async def process_sound_links(sound_links: List[str], session: aiohttp.ClientSession) -> List[str]:
    """Process sound links to get embed URLs."""
    embed_urls = []
    for link in sound_links:
        try:
            # Extract the music ID from the URL
            match = re.search(r'music/(\d+)', link)
            if match:
                music_id = match.group(1)
                # Construct the embed URL
                embed_url = f"https://www.tiktok.com/embed/music/{music_id}"
                embed_urls.append(embed_url)
                logger.info(f"Generated embed URL: {embed_url}")
            else:
                logger.warning(f"Could not extract music ID from URL: {link}")
        except Exception as e:
            logger.error(f"Error processing sound link {link}: {str(e)}")
    
    logger.info(f"Generated {len(embed_urls)} embed URLs from {len(sound_links)} sound links")
    return embed_urls 