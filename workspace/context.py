from .product import PRODUCT
from .domain import REGISTRY
def product(request):
    return {'product':PRODUCT, 'navigation':list(REGISTRY.items())}
