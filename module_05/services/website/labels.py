PROPERTY_TYPE_LABELS = {"apartment": "Apartamento", "house": "Casa"}
STATUS_LABELS = {"available": "Disponível", "sold": "Vendido", "rented": "Alugado"}


def property_type_label(property_type: str) -> str:
    return PROPERTY_TYPE_LABELS.get(property_type, property_type.capitalize())


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status.capitalize())
