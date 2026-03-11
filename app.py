from flask import Flask, request, send_file, jsonify
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import os
import textwrap

app = Flask(__name__)

def download_font():
    """Download a font that supports Cyrillic"""
    font_path = "/app/fonts/DejaVuSans-Bold.ttf"
    os.makedirs("/app/fonts", exist_ok=True)
    
    if not os.path.exists(font_path):
        # DejaVu supports Cyrillic perfectly
        url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans-Bold.ttf"
        r = requests.get(url, timeout=10)
        with open(font_path, "wb") as f:
            f.write(r.content)
    return font_path

def add_text_overlay(image_url: str, text: str) -> bytes:
    # Download image
    r = requests.get(image_url, timeout=15)
    img = Image.open(io.BytesIO(r.content)).convert("RGBA")
    
    width, height = img.size
    draw = ImageDraw.Draw(img)

    # Font size relative to image width
    font_size = max(48, width // 12)
    
    try:
        font_path = download_font()
        font = ImageFont.truetype(font_path, font_size)
    except Exception:
        font = ImageFont.load_default()

    # Wrap text to fit width
    max_chars = max(10, width // (font_size // 2))
    lines = textwrap.wrap(text, width=max_chars)
    
    # Calculate total text block height
    line_height = font_size + 12
    total_text_height = line_height * len(lines) + 40
    
    # Dark gradient overlay at top
    overlay = Image.new("RGBA", (width, total_text_height + 20), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    
    # Gradient from black to transparent
    for y in range(total_text_height + 20):
        alpha = int(180 * (1 - y / (total_text_height + 20)))
        overlay_draw.rectangle([0, y, width, y + 1], fill=(0, 0, 0, alpha))
    
    img.paste(overlay, (0, 0), overlay)
    
    # Draw each line of text centered
    draw = ImageDraw.Draw(img)
    y_start = 20
    
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (width - text_w) // 2
        
        # Shadow
        draw.text((x + 2, y_start + 2), line, font=font, fill=(0, 0, 0, 200))
        # White text
        draw.text((x, y_start), line, font=font, fill=(255, 255, 255, 255))
        y_start += line_height

    # Convert back to RGB for JPEG
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
        return send_file(
            io.BytesIO(result),
            mimetype="image/jpeg",
            as_attachment=False,
            download_name="result.jpg"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
