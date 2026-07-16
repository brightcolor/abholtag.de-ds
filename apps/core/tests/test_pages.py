"""Static content pages render and expose the data provenance."""


def test_data_provenance_page(client, db):
    response = client.get("/datenquelle/")
    content = response.content.decode()
    assert response.status_code == 200
    assert "Entsorgungsbetriebe Lübeck" in content
    assert "ohne Gewähr" in content
    # source of truth is linked
    assert "entsorgung.luebeck.de" in content


def test_data_provenance_linked_in_footer(client, db):
    content = client.get("/").content.decode()
    assert 'href="/datenquelle/"' in content


def test_imprint_and_privacy_still_render(client, db):
    assert client.get("/impressum/").status_code == 200
    assert client.get("/datenschutz/").status_code == 200
