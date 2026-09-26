from jarvis.startup.hud_companion import DoubleClap


def test_two_short_claps_wake_but_sustained_noise_does_not():
    detector = DoubleClap(threshold=0.2)
    assert not detector.feed(0.8, 10.0)
    assert not detector.feed(0.0, 10.06)
    assert not detector.feed(0.7, 10.45)
    assert detector.feed(0.0, 10.51)

    detector = DoubleClap(threshold=0.2)
    assert not detector.feed(0.8, 20.0)
    assert not detector.feed(0.8, 20.3)
    assert not detector.feed(0.0, 20.35)
    assert not detector.feed(0.8, 20.7)
    assert not detector.feed(0.0, 20.75)
