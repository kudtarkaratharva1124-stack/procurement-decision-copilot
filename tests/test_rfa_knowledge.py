from app.services.rfa_knowledge import RFAKnowledgeService


def test_nine_reference_files_loaded():
    service = RFAKnowledgeService()
    assert len(service.all()) == 9


def test_category_reference_retrieval():
    service = RFAKnowledgeService()
    rows = service.retrieve({'category': 'RFACU', 'subject': 'RFACU cost revision', 'body': 'commercial increase'}, limit=3)
    assert rows
    assert 'RFACU' in rows[0]['name']
