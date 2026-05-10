import enum


class RiskTier(str, enum.Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class Recommendation(str, enum.Enum):
    APPROVE = "approve"
    REVIEW = "review"
    DECLINE = "decline"


class EnrichmentSource(str, enum.Enum):
    CIPC = "cipc"
    TRANSUNION = "transunion"
    SARS = "sars"
    BANK_STATEMENT = "bank_statement"
    BANK_API = "bank_api"


class LenderTier(str, enum.Enum):
    TRIAL = "trial"
    STANDARD = "standard"
    ENTERPRISE = "enterprise"


class TurnoverBand(str, enum.Enum):
    UNDER_1M = "under_1m"
    BAND_1M_5M = "1m_5m"
    BAND_5M_20M = "5m_20m"
    BAND_20M_50M = "20m_50m"
    OVER_50M = "over_50m"


class EmployeeBand(str, enum.Enum):
    MICRO = "1-5"
    SMALL = "6-20"
    MEDIUM = "21-50"
    LARGE = "51-200"


class Province(str, enum.Enum):
    GAUTENG = "gauteng"
    WESTERN_CAPE = "western_cape"
    KWAZULU_NATAL = "kwazulu_natal"
    EASTERN_CAPE = "eastern_cape"
    FREE_STATE = "free_state"
    MPUMALANGA = "mpumalanga"
    LIMPOPO = "limpopo"
    NORTH_WEST = "north_west"
    NORTHERN_CAPE = "northern_cape"


class Confidence(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
