from flask import Flask, request, render_template, send_file, jsonify
import subprocess
import os
import uuid
import sys
import imageio_ffmpeg
import io

app = Flask(__name__)
DOWNLOAD_FOLDER = 'downloads'

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    url = data.get('url')
    start_time = data.get('start_time') 
    end_time = data.get('end_time')
    quality = data.get('quality', '1080')

    if not url or not start_time or not end_time:
        return jsonify({"error": "URL, Start Time, and End Time are required."}), 400

    if quality not in ['360', '480', '720', '1080']:
        quality = '1080'

    job_id = str(uuid.uuid4())
    output_filename = f"{job_id}.mp4"
    output_path = os.path.join(DOWNLOAD_FOLDER, output_filename)

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    vid_format = f"bv*[ext=mp4][vcodec^=avc1][height<={quality}]+ba[ext=m4a]/bv*[ext=mp4][height<={quality}]+ba[ext=m4a]/mp4"

    command = [
        sys.executable, "-m", "yt_dlp",
        "--ffmpeg-location", ffmpeg_exe,
        "--concurrent-fragments", "16",
        "--download-sections", f"*{start_time}-{end_time}",
        "-f", vid_format,
        "--merge-output-format", "mp4",
        "--recode-video", "mp4",
        "--postprocessor-args", "ffmpeg:-c:v libx264 -preset ultrafast -crf 23 -c:a aac -b:a 160k -vf scale=-2:1080 -pix_fmt yuv420p -movflags +faststart",
        "-o", output_path,
        url
    ]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        
        with open(output_path, 'rb') as f:
            video_data = io.BytesIO(f.read())
            
        return send_file(
            video_data, 
            as_attachment=True, 
            download_name=f"ytclipper_{start_time.replace(':','')}_to_{end_time.replace(':','')}_{quality}p.mp4",
            mimetype="video/mp4"
        )
    except subprocess.CalledProcessError as e:
        print("YT-DLP ERROR:", e.stderr)
        return jsonify({"error": e.stderr or "Download failed"}), 500
    finally:
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception as e:
                print(f"Cleanup error: {e}")

if __name__ == '__main__':
    app.run(debug=True, port=5000)