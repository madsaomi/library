from django.db import connection
from django.db.models import Q


def search_books(queryset, query, fields=("title", "author", "description", "category__name")):
    if not query:
        return queryset

    if connection.vendor == "postgresql":
        from django.contrib.postgres.search import SearchQuery, SearchVector, SearchRank
        vector = SearchVector(*fields)
        s_query = SearchQuery(query)
        return queryset.annotate(
            rank=SearchRank(vector, s_query)
        ).filter(rank__gte=0.01).order_by("-rank")

    q = Q()
    for field in fields:
        q |= Q(**{f"{field}__icontains": query})
    return queryset.filter(q)
