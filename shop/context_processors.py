from .models import ProductComment


def latest_comments(request):
    comments = (
        ProductComment.objects
        .filter(is_approved=True, parent__isnull=True)
        .select_related("product")
        .order_by("-id")[:15]
    )

    return {
        "latest_comments": comments
    }