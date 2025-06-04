async def get_posts(sources: list) -> list:
  from utils.telethon_fetcher import fetch_posts_for_category
  posts = await fetch_posts_for_category(sources)
  # Можна враховувати перегляди, лайки, коментарі
  return sorted(posts, key=lambda p: p.get("views", 0) + p.get("forwards", 0), reverse=True)
