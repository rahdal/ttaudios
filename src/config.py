import aiohttp

# HTTP Configuration
HTTP_TIMEOUT = aiohttp.ClientTimeout(total=30)  # 30 second timeout
MAX_CONNECTIONS = 10  # Maximum concurrent connections
CHUNK_SIZE = 32768  # 32KB chunks for downloads

# Audio Processing Configuration
AUDIO_DURATION = 15000  # 15 seconds in milliseconds
SAMPLE_RATE = 16000  # 16kHz sample rate
CHANNELS = 1  # Mono audio

# Retry Configuration
MAX_RETRIES = 1  # Maximum number of retries (1 retry = 2 tries total)
RETRY_WAIT = 1  # Fixed 1 second wait between retries

# TikTok Configuration
TIKTOK_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )
}

# Redirect Checker API Configuration
REDIRECT_CHECKER_API = "https://www.redirectchecker.org/api/redirectcheck"
REDIRECT_CHECKER_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "insomnia/9.2.0"
} 