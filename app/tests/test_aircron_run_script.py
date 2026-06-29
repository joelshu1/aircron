from pathlib import Path


def test_apple_music_speaker_volume_uses_airplay_sound_volume() -> None:
    script = Path(__file__).resolve().parents[2] / "aircron_run.sh"
    text = script.read_text()

    assert "set sound volume of d to ${pct}" in text
    assert "set volume of d to ${pct}" not in text
    assert "Apple Music AirPlay device not found" in text
