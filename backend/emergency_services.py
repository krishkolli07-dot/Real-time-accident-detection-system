import requests

def nearby_services(lat, lon):
    try:
        url = f"https://overpass-api.de/api/interpreter?data=[out:json];(node[amenity=hospital](around:5000,{lat},{lon});node[amenity=ambulance_station](around:5000,{lat},{lon});node[amenity=police](around:5000,{lat},{lon}));out;"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Services lookup failed: {e}")
        return {"elements": []}
