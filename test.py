import requests
import json

def get_tiktok_music_data(music_id):
    """
    Fetches TikTok music data based on a given music ID.
    
    Parameters:
        music_id (str): The unique ID of the TikTok music track.
        
    Returns:
        dict: JSON response containing music-related data.
    """

    # Base URL for TikTok's API
    base_url = "https://www.tiktok.com/api/music/item_list/"

    # Define query parameters (dynamically include music ID)
    params = {
        "WebIdLastTime": "1734736397",
        "aid": "1988",
        "app_language": "en",
        "app_name": "tiktok_web",
        "browser_language": "en-US",
        "browser_name": "Mozilla",
        "browser_online": "true",
        "browser_platform": "MacIntel",
        "browser_version": "5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
        "channel": "tiktok_web",
        "cookie_enabled": "true",
        "count": "30",
        "coverFormat": "0",
        "cursor": "0",
        "data_collection_enabled": "true",
        "device_id": "7450636053261436462",
        "device_platform": "web_pc",
        "focus_state": "true",
        "from_page": "music",
        "history_len": "1",
        "is_fullscreen": "false",
        "is_page_visible": "true",
        "language": "en",
        "musicID": music_id,  # Dynamically insert the music ID here
        "odinId": "6762869605875975174",
        "os": "mac",
        "priority_region": "US",
        "referer": "https://www.tiktok.com/",
        "region": "US",
        "screen_height": "1366",
        "screen_width": "1024",
        "tz_name": "America/Detroit",
        "user_is_login": "true",
        "verifyFp": "verify_m6vhcmfo_XOD9IKzM_rxW2_4QTr_A8sD_rDHQk5AALZC0",
        "webcast_language": "en",
        "msToken": "FTJmVgZGZKYvNzF7rN3oDVAAaiJGKWueuwKa8wzHvKa64QCJQx5RAHijH6axtGD76rORIW72HNIumLbi8mlvBW8OdVQIIbILf0n2mAD6NMAvIwxBSprJ_6HLmOnWS9gefzc6-Xrh_8yPA2GRIVtg--y8FtE=",
        "X-Bogus": "DFSzsIVOgPiANn-9t4/cMDLNKBOI",
        "_signature": "_02B4Z6wo0000125GJYQAAIDAPLkFnHMAuIduRCEAALxS9b"
    }

    # Set headers to mimic a real browser request
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.tiktok.com/",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive"
    }

    # Send the GET request
    response = requests.get(base_url, headers=headers, params=params)

    # Handle response
    if response.status_code == 200:
        return response.json()  # Return parsed JSON response
    else:
        print(f"⚠️ Failed to retrieve data. Status code: {response.status_code}")
        return None

# Example Usage
music_id = "7473667826038343696"  # Replace with any TikTok music ID
data = get_tiktok_music_data(music_id)

# Print formatted JSON response
if data:
    print(json.dumps(data, indent=4))
