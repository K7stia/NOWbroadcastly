async def get_posts(sources: list) -> list:
  from utils.telethon_fetcher import fetch_posts_for_category
  posts = await fetch_posts_for_category(sources)
  return sorted(posts, key=lambda p: p.get("date", ""), reverse=True)
