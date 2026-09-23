PROPERTY_TYPE_LABELS = {"apartment": "Apartamento", "house": "Casa"}


def property_type_label(property_type: str) -> str:
    return PROPERTY_TYPE_LABELS.get(property_type, property_type.capitalize())
