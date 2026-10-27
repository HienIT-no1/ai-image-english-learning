"""Real regression photo; model downloads are an explicit setup step."""
from pathlib import Path
import io
import numpy as np
import pytest
from PIL import Image
from app.services.ai_detection import decode_image, detect_candidates

ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.skipif(not (ROOT/'weights/yolo11n.pt').exists(),reason='Run python setup_ai_models.py for the real-model regression')
def test_red_apple_photo_is_not_labelled_pomegranate():
    image=decode_image((Path(__file__).parent/'fixtures/red_apple.jpg').read_bytes())
    results=detect_candidates(image,.35)
    assert any(r.label.lower()=='apple' for r in results)
    assert not any(r.label.lower()=='pomegranate' for r in results)

def test_uniform_colors_are_not_treated_as_objects():
    for color in [(255,255,255),(0,0,0),(255,0,0),(0,255,0),(0,0,255)]:
        assert detect_candidates(np.full((64,64,3),color,dtype=np.uint8),.35)==[]

def test_exif_orientation_is_applied_before_predicting():
    original=Image.new('RGB',(30,50),'white');exif=original.getexif();exif[274]=6
    stream=io.BytesIO();original.save(stream,'JPEG',exif=exif)
    image=decode_image(stream.getvalue())
    assert image.shape[:2]==(30,50)
