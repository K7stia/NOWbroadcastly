from monitoring_models.popular import get_posts as popular_model
from monitoring_models.latest import get_posts as latest_model
from monitoring_models.trending import get_posts as trending_model

model_registry = {
    "popular": popular_model,
    "latest": latest_model,
    "trending": trending_model,
}
