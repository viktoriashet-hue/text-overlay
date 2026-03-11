from flask import Flask, request, send_file, jsonify
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import os
import textwrap

app = Flask(__name__)

def get_font(size):
    font_path = "/tmp/DejaVuSans-Bold.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans-Bold.ttf"
        r = requests.get(url, timeout=15)
        with open(font_path, "wb") as f:
            f.write(r.content)
    return ImageFont.truetype(font_path, size)

def add_text_overlay(image_url: str, text: str) -> bytes:
    r = requests.get(image_url, timeout=15)
    img = Image.open(io.BytesIO(r.content)).convert("RGBA")
    width, height = img.size

    font_size = max(48, width // 10)
    try:
        font = get_font(font_size)
    except:
        font = ImageFont.load_default()

    max_chars = max(10, width // (font_size // 2))
    lines = textwrap.wrap(text, width=max_chars)
    line_height = font_size + 16
    total_height = line_height * len(lines) + 60

    overlay = Image.new("RGBA", (width, total_height), (0, 0, 0, 160))
    img.paste(overlay, (0, 0), overlay)

    draw = ImageDraw.Draw(img)
    y = 20
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (width - text_w) // 2
        draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0, 255))
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        y += line_height

    final = img.convert("RGB")
    buf = io.BytesIO()
    final.save(buf, format="JPEG", quality=92)
    buf.seek(0)
    return buf.getvalue()

@app.route("/overlay", methods=["POST"])
def overlay():
    data = request.get_json()
    image_url = data.get("image_url")
    text = data.get("text", "")
    if not image_url or not text:
        return jsonify({"error": "image_url and text required"}), 400
    try:
        result = add_text_overlay(image_url, text)
        return send_file(io.BytesIO(result), mimetype="image/jpeg")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
```

И `Procfile` замени на:
```
web: gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120
