import requests

# 🔐 Замінити ці значення своїми
PAGE_ID = "226112651190161"  # ID твоєї сторінки
ACCESS_TOKEN = "EAAPquIRTBaQBO6kkSnNnd3YxZBZCWI8cQHJRK2PIVkKvCLPbng5EC31YC2VUzEDwUuZCALeWsqKxzEvbcX9kLiHEKsz8bJYmRx6XfS99LUjUF2vaZASDzWwDDmv3JgFOYwUJTAVg3FRaVthZCnnMZBkkWDKE6q1SwazVpLIs1j0xgHdKcsqZABf7opXEDH62CkW2sjwU3uFzNu9FAk5B9ZACobcREDFZAjtPEZCJh8"     # Page Access Token
MESSAGE = "Вітаю!"

url = f"https://graph.facebook.com/v22.0/{PAGE_ID}/feed"
params = {
    "message": MESSAGE,
    "access_token": ACCESS_TOKEN
}

response = requests.post(url, params=params)

if response.status_code == 200:
    print("✅ Пост опубліковано!")
    print("🔗 ID поста:", response.json()["id"])
else:
    print("❌ Помилка при публікації")
    print("Status:", response.status_code)
    print(response.json())
