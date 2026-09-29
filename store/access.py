from django.db.models import Q

from account.models import Company


STORE_COMPANY_SESSION_KEY = 'active_store_company_id'


def accessible_store_companies(user):
    """Companies whose warehouse the user may manage."""
    if not user.is_authenticated:
        return Company.objects.none()
    return Company.objects.filter(Q(manager=user) | Q(users=user)).distinct().order_by('name')


def active_store_company(request):
    companies = accessible_store_companies(request.user)
    company = companies.filter(pk=request.session.get(STORE_COMPANY_SESSION_KEY)).first()
    if company is None:
        company = companies.filter(manager=request.user).first() or companies.first()
        if company is not None:
            request.session[STORE_COMPANY_SESSION_KEY] = company.pk
    return company
