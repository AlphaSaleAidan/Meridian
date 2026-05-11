from .base import BaseCrossRefAgent, CrossRefContext
from .path_to_purchase_agent import PathToPurchaseAgent
from .zone_conversion_agent import ZoneConversionAgent
from .lost_sale_agent import LostSaleAgent
from .influence_zone_agent import InfluenceZoneAgent
from .staff_effect_agent import StaffEffectAgent
from .peak_basket_agent import PeakBasketAgent
from .return_customer_agent import ReturnCustomerAgent
from .queue_basket_agent import QueueBasketAgent
from .posture_purchase_agent import PosturePurchaseAgent
from .product_placement_agent import ProductPlacementAgent

ALL_CROSS_REF_AGENTS = [
    PathToPurchaseAgent,
    ZoneConversionAgent,
    LostSaleAgent,
    InfluenceZoneAgent,
    StaffEffectAgent,
    PeakBasketAgent,
    ReturnCustomerAgent,
    QueueBasketAgent,
    PosturePurchaseAgent,
    ProductPlacementAgent,
]
