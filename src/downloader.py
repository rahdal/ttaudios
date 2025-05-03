import logging
import aiohttp
import asyncio
import json
from typing import Optional, List, Dict
from .config import (
    HTTP_TIMEOUT,
    MAX_RETRIES,
    RETRY_WAIT,
    CHUNK_SIZE,
    TIKTOK_HEADERS,
    REDIRECT_CHECKER_API,
    REDIRECT_CHECKER_HEADERS
)

logger = logging.getLogger(__name__)

async def download_audio_with_retry(url: str, output_path: str, session: aiohttp.ClientSession) -> bool:
    """Download audio file with retry logic."""
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Downloading audio from {url} (attempt {attempt + 1}/{MAX_RETRIES})")
            
            async with session.get(url, headers=TIKTOK_HEADERS, timeout=HTTP_TIMEOUT) as response:
                if response.status == 200:
                    with open(output_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(CHUNK_SIZE):
                            f.write(chunk)
                    logger.info(f"Successfully downloaded audio to {output_path}")
                    return True
                elif response.status in [429, 500, 502, 503, 504]:
                    wait_time = RETRY_WAIT * (2 ** attempt)
                    logger.warning(f"Server error {response.status}. Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to download audio: HTTP {response.status}")
                    return False
                    
        except asyncio.TimeoutError:
            logger.warning(f"Timeout on attempt {attempt + 1}. Retrying...")
            await asyncio.sleep(RETRY_WAIT * (2 ** attempt))
        except Exception as e:
            logger.error(f"Error downloading audio: {str(e)}")
            if attempt == MAX_RETRIES - 1:
                return False
            await asyncio.sleep(RETRY_WAIT * (2 ** attempt))
    
    return False

async def check_redirect(url: str, session: aiohttp.ClientSession) -> Optional[str]:
    """Check if URL redirects using the redirect checker API and return final URL."""
    try:
        logger.info(f"Checking redirects for URL: {url}")
        
        # Prepare the request payload
        payload = {"url": url}
        
        # Make the API request
        async with session.post(
            REDIRECT_CHECKER_API,
            headers=REDIRECT_CHECKER_HEADERS,
            json=payload,
            timeout=HTTP_TIMEOUT
        ) as response:
            if response.status == 200:
                redirect_data = await response.json()
                if isinstance(redirect_data, list) and len(redirect_data) > 0:
                    # Get the last redirect in the chain
                    final_redirect = redirect_data[-1]
                    if final_redirect["status"] == 200:
                        final_url = final_redirect["url"]
                        logger.info(f"Final URL after redirects: {final_url}")
                        return final_url
                    else:
                        logger.warning(f"Final redirect status not 200: {final_redirect['status']}")
                else:
                    logger.warning("No redirect data returned from API")
            else:
                logger.error(f"Redirect checker API returned status {response.status}")
        
        return None
    except Exception as e:
        logger.error(f"Error checking redirect for {url}: {str(e)}")
        return None 