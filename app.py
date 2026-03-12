from flask import Flask, request, send_file, jsonify
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import os

app = Flask(__name__)

def get_font(size):
    font_path = "/app/fonts/DejaVuSans-Bold.ttf"
    if os.path.exists(font_path):
        return ImageFont.truetype(font_path, size)
    return ImageFont.load_default()

def wrap_text_pixels(text, font, max_width, draw):
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = (current_line + " " + word).strip()
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines

def add_text_overlay(image_url, text):
    r = requests.get(image_url, timeout=15)
    img = Image.open(io.BytesIO(r.content)).convert("RGBA")
    width, height = img.size
    font_size = max(32, width // 14)
    try:
        font = get_font(font_size)
    except:
        font = ImageFont.load_default()
    draw = ImageDraw.Draw(img)
    max_width = width - 40
    lines = wrap_text_pixels(text, font, max_width, draw)
    line_height = font_size + 12
    total_height = line_height * len(lines) + 40
    overlay_y = (height - total_height) // 2
    overlay = Image.new("RGBA", (width, total_height), (0, 0, 0, 180))
    img.paste(overlay, (0, overlay_y), overlay)
    draw = ImageDraw.Draw(img)
    y = overlay_y + 15
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
