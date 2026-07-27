from django.db import connection
from django.db.models import Q


def search_books(queryset, query):
    if not query:
        return queryset

    if connection.vendor == 'postgresql':
        from django.contrib.postgres.search import SearchQuery, SearchRank

        from .models import book_search_vector

        vector = book_search_vector()
        s_query = SearchQuery(query, config='simple')
        return queryset.annotate(rank=SearchRank(vector, s_query)).filter(rank__gte=0.01).order_by('-rank')

    q = (
        Q(title__icontains=query)
        | Q(author__icontains=query)
        | Q(description__icontains=query)
        | Q(category__name__icontains=query)
    )
    return queryset.filter(q)
