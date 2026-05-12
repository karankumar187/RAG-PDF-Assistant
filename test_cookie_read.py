import urllib.parse
import json

raw_cookie = '%7B%22name%22%3A%20%22test%22%7D'
try:
    decoded = urllib.parse.unquote(raw_cookie)
    parsed = json.loads(decoded)
    print("Parsed:", parsed)
except Exception as e:
    print("Error:", e)

# What if cookie_controller sets it as a URL encoded string of a JSON string? e.g. %22%7B%5C%22name%5C%22...%22
raw_cookie2 = urllib.parse.quote('{"name": "test"}')
print(f"Quoted: {raw_cookie2}")
