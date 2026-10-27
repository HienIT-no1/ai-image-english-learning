`red_apple.jpg`: Abhijit Tembhekar, **Red Apple**, CC BY 2.0.
Source: https://commons.wikimedia.org/wiki/File:Red_Apple.jpg
License: https://creativecommons.org/licenses/by/2.0/
Test copy resized to 1280 pixels and JPEG-compressed.

Regression: the custom model alone predicted pomegranate (0.692); the independent
YOLO11n detector predicted apple (0.893) on the same object. This photo checks that
case; it does not measure overall accuracy. Unit tests also ensure low confidence,
unrelated boxes and unsupported reference classes cannot trigger replacements.
