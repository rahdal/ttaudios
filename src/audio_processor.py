import os
import logging
import tempfile
from pydub import AudioSegment
from typing import Optional, Dict, Set, List
import shazamio
from .config import AUDIO_DURATION, SAMPLE_RATE, CHANNELS
from .downloader import download_audio_with_retry
import asyncio
import aiohttp

logger = logging.getLogger(__name__)

# Global flag to track if we've found a match
found_match = False
current_tasks: Set[asyncio.Task] = set()

def signal_handler(signum, frame):
    """Handle SIGINT (Ctrl+C) to clean up tasks"""
    global current_tasks
    for task in current_tasks:
        task.cancel()
    logger.info("Received interrupt signal, cleaning up...")
    exit(0)

async def identify_song(audio_file_path: str) -> Optional[Dict]:
    """Identify a song using Shazam."""
    try:
        # Initialize Shazam with default settings
        shazam = shazamio.Shazam()
        
        # Recognize the song
        logger.info("Sending audio to Shazam for recognition...")
        
        # Read the audio file
        with open(audio_file_path, 'rb') as f:
            audio_data = f.read()
        
        # Send to Shazam with just the audio data
        result = await shazam.recognize_song(audio_data)
        
        if result and 'track' in result:
            track = result['track']
            song_info = {
                'title': track.get('title', 'Unknown'),
                'artist': track.get('subtitle', 'Unknown'),
                'album': track.get('sections', [{}])[0].get('metadata', [{}])[0].get('text', 'Unknown'),
                'shazam_id': track.get('key', 'Unknown')
            }
            logger.info(f"Successfully identified song: {song_info['title']} by {song_info['artist']}")
            return song_info
        else:
            logger.warning("Could not identify song - no track information found")
            return None
    except Exception as e:
        logger.error(f"Error identifying song: {str(e)}")
        return None

def convert_audio_to_wav(input_path: str, output_path: str) -> bool:
    """Convert audio file to WAV format with optimized parameters."""
    try:
        logger.info(f"Converting audio to WAV format: {input_path} -> {output_path}")
        # Load the audio file
        audio = AudioSegment.from_file(input_path)
        
        # Only use the first AUDIO_DURATION seconds of audio
        audio = audio[:AUDIO_DURATION * 1000]  # Convert seconds to milliseconds
        
        # Convert to WAV format with optimized parameters
        audio = audio.set_frame_rate(SAMPLE_RATE).set_channels(CHANNELS)
        
        # Export as WAV
        audio.export(output_path, format="wav")
        logger.info("Audio conversion successful")
        return True
    except Exception as e:
        logger.error(f"Error converting audio: {str(e)}")
        return False

async def download_audio_with_retry(url: str, temp_mp3_path: str, session: aiohttp.ClientSession, max_retries: int = 3) -> bool:
    """Download audio file with retry logic."""
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Downloading audio from {url} (attempt {attempt + 1}/{max_retries + 1})")
            async with session.get(url) as response:
                response.raise_for_status()
                
                # Write the audio data to the temporary file
                logger.debug("Writing audio data to temporary file...")
                with open(temp_mp3_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(32768):  # 32KB chunks
                        f.write(chunk)
                
                logger.info(f"Successfully downloaded audio to {temp_mp3_path}")
                return True
            
        except asyncio.TimeoutError:
            logger.warning(f"Timeout while downloading {url} (attempt {attempt + 1})")
            if attempt < max_retries:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.info(f"Waiting {wait_time} seconds before retry...")
                await asyncio.sleep(wait_time)
            continue
        except Exception as e:
            logger.error(f"Error downloading {url}: {str(e)}")
            if attempt < max_retries:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.info(f"Waiting {wait_time} seconds before retry...")
                await asyncio.sleep(wait_time)
            continue
    
    logger.error(f"Failed to download {url} after {max_retries} attempts")
    return False

async def download_video_with_retry(url: str, session: aiohttp.ClientSession, max_retries: int = 3) -> Optional[tempfile.NamedTemporaryFile]:
    """Download video file with retry logic."""
    for attempt in range(max_retries):
        try:
            # Use longer timeouts for video downloads
            timeout = aiohttp.ClientTimeout(
                total=30,  # Total timeout for the entire request
                connect=10,  # Timeout for establishing connection
                sock_read=10  # Timeout for reading from socket
            )
            
            async with session.get(url, timeout=timeout) as response:
                if response.status == 200:
                    # Create a temporary file with delete=False to manage it ourselves
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                    try:
                        # Write the content in chunks to avoid memory issues
                        async for chunk in response.content.iter_chunked(8192):
                            temp_file.write(chunk)
                        temp_file.close()  # Close the file handle
                        return temp_file
                    except Exception as e:
                        # Clean up the temporary file if there's an error
                        try:
                            os.unlink(temp_file.name)
                        except:
                            pass
                        raise e
                elif response.status == 403:
                    logger.warning(f"Access forbidden for URL: {url}")
                    return None
                else:
                    logger.warning(f"Failed to download video: HTTP {response.status}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        return None
        except asyncio.TimeoutError:
            logger.warning(f"Timeout downloading video (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
            else:
                return None
        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
            else:
                return None
    return None

def extract_audio_from_video(video_path: str) -> Optional[tempfile.NamedTemporaryFile]:
    """Extract first 15 seconds of audio from video file."""
    try:
        # Load the video file
        video = AudioSegment.from_file(video_path, format="mp4")
        
        # Extract first 15 seconds
        audio = video[:15000]  # 15 seconds in milliseconds
        
        # Convert to mono and set sample rate to 16kHz (Shazam's preferred format)
        audio = audio.set_channels(1).set_frame_rate(16000)
        
        # Create a temporary file for the audio
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        try:
            # Export as WAV with specific parameters
            audio.export(
                temp_file.name,
                format="wav",
                parameters=["-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1"]
            )
            temp_file.close()  # Close the file handle
            return temp_file
        except Exception as e:
            # Clean up the temporary file if there's an error
            try:
                os.unlink(temp_file.name)
            except:
                pass
            raise e
    except Exception as e:
        logger.error(f"Error extracting audio: {str(e)}")
        return None

async def process_single_video_url(video_url: str, session: aiohttp.ClientSession) -> Optional[Dict]:
    """Process a single video URL to identify the song."""
    try:
        # Download video
        video_file = await download_video_with_retry(video_url, session)
        if not video_file:
            return None
            
        try:
            # Extract audio
            audio_file = extract_audio_from_video(video_file.name)
            if not audio_file:
                return None
                
            try:
                # Send to Shazam with retries
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        result = await identify_song(audio_file.name)
                        if result:
                            return result
                    except Exception as e:
                        logger.error(f"Error in Shazam recognition (attempt {attempt + 1}/{max_retries}): {str(e)}")
                        if attempt < max_retries - 1:
                            logger.warning(f"Retrying Shazam recognition (attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        else:
                            return None
                return None
            finally:
                # Clean up audio file
                try:
                    os.unlink(audio_file.name)
                except:
                    pass
        finally:
            # Clean up video file
            try:
                os.unlink(video_file.name)
            except:
                pass
    except Exception as e:
        logger.error(f"Error processing video URL: {str(e)}")
        return None

async def process_audio_urls_parallel(video_urls: List[str], session: aiohttp.ClientSession) -> List[Dict]:
    """Process multiple video URLs in parallel to identify songs."""
    if not video_urls:
        logger.warning("No video URLs provided")
        return []

    # Create a semaphore to limit concurrent processing
    semaphore = asyncio.Semaphore(3)  # Limit to 3 concurrent processes
    
    async def process_with_semaphore(url):
        async with semaphore:
            try:
                return await process_single_video_url(url, session)
            except Exception as e:
                logger.error(f"Error processing video URL {url}: {str(e)}")
                return None
    
    # Process URLs in parallel with error handling
    tasks = [process_with_semaphore(url) for url in video_urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out None results and exceptions
    successful_results = [result for result in results if result is not None and not isinstance(result, Exception)]
    
    if successful_results:
        logger.info(f"Successfully identified {len(successful_results)} songs")
    else:
        logger.warning("No successful song identifications found")
    
    return successful_results 