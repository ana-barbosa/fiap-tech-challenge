from labels import property_type_label, status_label


def test_property_type_label_translates_known_types():
    assert property_type_label("apartment") == "Apartamento"
    assert property_type_label("house") == "Casa"


def test_property_type_label_falls_back_to_capitalized_value():
    assert property_type_label("loft") == "Loft"


def test_status_label_translates_known_statuses():
    assert status_label("available") == "Disponível"
    assert status_label("sold") == "Vendido"
    assert status_label("rented") == "Alugado"


def test_status_label_falls_back_to_capitalized_value():
    assert status_label("reserved") == "Reserved"
