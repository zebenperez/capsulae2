from .access import active_store_company, accessible_store_companies


def store_company(request):
    return {
        'store_company': active_store_company(request),
        'store_companies': accessible_store_companies(request.user),
    }
