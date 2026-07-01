"""v5.7 incrément 3 — bornage des flux longs (SSE/MJPEG) anti-épuisement."""


def test_stream_slots_are_bounded(J):
    # Sature les slots puis vérifie le refus, et la libération.
    acquired = 0
    try:
        while J._acquire_stream_slot():
            acquired += 1
            if acquired > J._STREAM_MAX + 5:
                break
        assert acquired == J._STREAM_MAX          # plafond respecté
        assert J._acquire_stream_slot() is False  # refus au-delà
    finally:
        for _ in range(acquired):
            J._release_stream_slot()
    # Après libération, on peut de nouveau acquérir.
    assert J._acquire_stream_slot() is True
    J._release_stream_slot()
