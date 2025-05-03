import asyncio
import logging
import sys
from typing import List, Dict
import aiohttp
from .tiktok_processor import (
    load_tiktok_data,
    extract_sound_links,
    process_sound_links,
    extract_video_tags_from_embed,
    extract_audio_urls_from_video_tags
)
from .audio_processor import process_audio_urls_parallel
from .config import TIKTOK_HEADERS
import argparse
import json

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

async def process_single_embed_url(embed_url: str, session: aiohttp.ClientSession) -> List[Dict]:
    """Process a single embed URL and return any identified songs."""
    logger = logging.getLogger(__name__)
    results = []
    
    try:
        logger.info(f"Processing embed URL: {embed_url}")
        
        # Fetch embed page
        logger.info(f"Fetching TikTok embed page: {embed_url}")
        video_tags = await extract_video_tags_from_embed(embed_url, session)
        if not video_tags:
            logger.warning(f"No video tags found in embed page: {embed_url}")
            return results
        
        # Extract video URLs
        logger.info("Extracting video URLs from video tags")
        video_urls = extract_audio_urls_from_video_tags(video_tags)
        if not video_urls:
            logger.warning(f"No video URLs found in embed page: {embed_url}")
            return results
        
        logger.info(f"Found {len(video_urls)} video URLs to process")
        
        # Process video URLs
        results = await process_audio_urls_parallel(video_urls, session)
        if results:
            logger.info(f"Found {len(results)} songs for embed URL: {embed_url}")
        else:
            logger.warning(f"No songs identified for embed URL: {embed_url}")
            
    except Exception as e:
        logger.error(f"Error processing embed URL {embed_url}: {str(e)}")
    
    return results

async def main():
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Process TikTok data and identify songs')
    parser.add_argument('input_file', help='Path to the TikTok data JSON file')
    args = parser.parse_args()

    try:
        # Load TikTok data
        logger.info(f"Loading TikTok data from {args.input_file}")
        tiktok_data = load_tiktok_data(args.input_file)
        if not tiktok_data:
            logger.error("Failed to load TikTok data")
            return

        # Extract sound links
        logger.info("Extracting sound links from TikTok data")
        sound_links = extract_sound_links(tiktok_data)
        if not sound_links:
            logger.error("No sound links found in TikTok data")
            return

        # Generate embed URLs
        logger.info("Generating embed URLs from sound links")
        embed_urls = []
        for link in sound_links:
            # Extract music ID from the URL
            music_id = link.split('/')[-1]
            if music_id.endswith('.html'):
                music_id = music_id[:-5]  # Remove .html extension
            embed_url = f"https://www.tiktok.com/embed/music/{music_id}"
            embed_urls.append(embed_url)
        logger.info(f"Generated {len(embed_urls)} embed URLs from {len(sound_links)} sound links")

        # Process embed URLs in parallel
        logger.info(f"Processing {len(embed_urls)} embed URLs")
        all_results = []
        
        # Create a connection pool with limits
        connector = aiohttp.TCPConnector(
            limit=5,  # Maximum number of concurrent connections
            limit_per_host=2,  # Maximum number of concurrent connections per host
            ssl=False,  # Disable SSL verification to reduce overhead
            force_close=True  # Force close connections after use
        )
        
        # Create a semaphore to limit concurrent processing
        semaphore = asyncio.Semaphore(5)  # Limit to 5 concurrent processes
        
        # Create a session with longer timeouts
        timeout = aiohttp.ClientTimeout(
            total=30,  # Total timeout for the entire request
            connect=10,  # Timeout for establishing connection
            sock_read=10  # Timeout for reading from socket
        )
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=TIKTOK_HEADERS
        ) as session:
            # Process URLs in smaller batches to avoid overwhelming the system
            batch_size = 5  # Reduced batch size
            for i in range(0, len(embed_urls), batch_size):
                batch = embed_urls[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1} of {(len(embed_urls) + batch_size - 1)//batch_size}")
                
                try:
                    # Process batch in parallel
                    batch_results = await asyncio.gather(*[
                        process_single_embed_url(url, session) for url in batch
                    ])
                    
                    # Flatten results
                    for results in batch_results:
                        all_results.extend(results)
                    
                    # Save results after each batch
                    if all_results:
                        output_file = "identified_songs.json"
                        with open(output_file, 'w') as f:
                            json.dump(all_results, f, indent=2)
                        logger.info(f"Saved {len(all_results)} identified songs to {output_file}")
                    
                    # Add a longer delay between batches to avoid rate limiting
                    if i + batch_size < len(embed_urls):
                        await asyncio.sleep(5)  # Increased delay between batches
                        
                except Exception as e:
                    logger.error(f"Error processing batch: {str(e)}")
                    continue

        if not all_results:
            logger.warning("No songs were identified")

    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 