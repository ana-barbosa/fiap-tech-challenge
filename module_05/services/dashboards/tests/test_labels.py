from labels import property_type_label


def test_property_type_label_translates_known_types():
    assert property_type_label("apartment") == "Apartamento"
    assert property_type_label("house") == "Casa"


def test_property_type_label_falls_back_to_capitalized_value():
    assert property_type_label("loft") == "Loft"
