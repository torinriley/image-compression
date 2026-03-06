import os
import io
import uuid
import tempfile
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_file
from PIL import Image

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB upload limit

UPLOAD_DIR = tempfile.mkdtemp(prefix="imgcrush_")

# ─────────────────────────────────────────────
#  COMPRESSION ENGINE
# ─────────────────────────────────────────────

def get_file_size_kb(path):
    return os.path.getsize(path) / 1024


def compress_image(input_path, output_path, target_kb, output_format, resize_w, resize_h):
    img = Image.open(input_path)

    if output_format == "JPEG" and img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    original_size = (img.width, img.height)

    if resize_w and resize_h:
        img = img.resize((resize_w, resize_h), Image.LANCZOS)
    elif resize_w:
        ratio = resize_w / img.width
        img = img.resize((resize_w, int(img.height * ratio)), Image.LANCZOS)
    elif resize_h:
        ratio = resize_h / img.height
        img = img.resize((int(img.width * ratio), resize_h), Image.LANCZOS)

    if output_format == "PNG":
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        result_kb = buffer.tell() / 1024
        quality_used = "lossless"
        with open(output_path, "wb") as f:
            f.write(buffer.getvalue())
        return result_kb, quality_used, original_size, (img.width, img.height)

    low, high, best_buf, best_q = 1, 95, None, 95
    for _ in range(12):
        mid = (low + high) // 2
        buf = io.BytesIO()
        img.save(buf, format=output_format, quality=mid, optimize=True)
        size_kb = buf.tell() / 1024
        if size_kb <= target_kb:
            best_buf, best_q = buf, mid
            low = mid + 1
        else:
            high = mid - 1

    if best_buf is None:
        best_buf = io.BytesIO()
        img.save(best_buf, format=output_format, quality=1, optimize=True)
        best_q = 1

    result_kb = best_buf.tell() / 1024
    with open(output_path, "wb") as f:
        f.write(best_buf.getvalue())

    return result_kb, best_q, original_size, (img.width, img.height)


# ─────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify(error="No file provided"), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify(error="Empty filename"), 400

    file_id = uuid.uuid4().hex
    ext = Path(file.filename).suffix
    save_path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")
    file.save(save_path)

    size_kb = get_file_size_kb(save_path)
    img = Image.open(save_path)
    w, h = img.width, img.height
    img.close()

    return jsonify(
        file_id=file_id,
        filename=file.filename,
        size_kb=round(size_kb, 1),
        width=w,
        height=h,
        ext=ext,
    )


@app.route("/preview/<file_id>")
def preview(file_id):
    for f in os.listdir(UPLOAD_DIR):
        if f.startswith(file_id):
            path = os.path.join(UPLOAD_DIR, f)
            img = Image.open(path)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.thumbnail((600, 600), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            buf.seek(0)
            return send_file(buf, mimetype="image/jpeg")
    return jsonify(error="Not found"), 404


@app.route("/compress", methods=["POST"])
def compress():
    data = request.get_json()
    file_id = data.get("file_id")
    fmt = data.get("format", "JPEG").upper()
    target_size = float(data.get("target_size", 200))
    unit = data.get("unit", "KB")
    resize_w = data.get("resize_w") or None
    resize_h = data.get("resize_h") or None

    if resize_w:
        resize_w = int(resize_w)
    if resize_h:
        resize_h = int(resize_h)

    target_kb = target_size if unit == "KB" else target_size * 1024

    input_path = None
    for f in os.listdir(UPLOAD_DIR):
        if f.startswith(file_id) and "_compressed" not in f:
            input_path = os.path.join(UPLOAD_DIR, f)
            break

    if not input_path:
        return jsonify(error="File not found"), 404

    ext_map = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
    out_id = file_id + "_compressed"
    output_path = os.path.join(UPLOAD_DIR, f"{out_id}{ext_map[fmt]}")

    try:
        result_kb, quality, orig_dim, new_dim = compress_image(
            input_path, output_path, target_kb, fmt, resize_w, resize_h
        )
    except Exception as e:
        return jsonify(error=str(e)), 500

    orig_kb = get_file_size_kb(input_path)
    reduction = (1 - result_kb / orig_kb) * 100 if orig_kb > 0 else 0

    return jsonify(
        compressed_id=out_id,
        original_kb=round(orig_kb, 1),
        result_kb=round(result_kb, 1),
        reduction=round(reduction, 1),
        quality=quality,
        original_dim=f"{orig_dim[0]}\u00d7{orig_dim[1]}",
        new_dim=f"{new_dim[0]}\u00d7{new_dim[1]}",
        format=fmt,
    )


@app.route("/download/<file_id>")
def download(file_id):
    for f in os.listdir(UPLOAD_DIR):
        if f.startswith(file_id):
            path = os.path.join(UPLOAD_DIR, f)
            return send_file(path, as_attachment=True, download_name=f"compressed{Path(f).suffix}")
    return jsonify(error="Not found"), 404


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n  IMGCRUSH running at http://localhost:5050\n")
    app.run(debug=True, port=5050)

