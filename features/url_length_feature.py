"""
Feature 2. URL Length
URL 전체 길이를 기준으로 피싱 여부를 판단한다.
반환값:
     1 : 길이 < 54
     0 : 54 <= 길이 <= 75
    -1 : 길이 > 75
"""

def url_length_feature(url: str) -> int:
    length = len(url)
    
    if length < 54:
        return 1
    elif length <= 75:
        return 0
    else:
        return -1
    
