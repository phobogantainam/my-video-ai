import os
import base64
import io
import google.generativeai as genai
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image

# --- CẤU HÌNH BAN ĐẦU ---
load_dotenv()
try:
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
except Exception as e:
    print(f"CRITICAL: Failed to configure Gemini API, likely missing API key. Error: {e}")

# --- KHỞI TẠO ỨNG DỤNG WEB ---
app = Flask(__name__)
CORS(app)

# --- CÁC HÀM LÕI ĐÃ TỐI ƯU HÓA ---

def tao_anh_tu_text(prompt: str, aspect_ratio: str) -> bytes:
    """Tạo ảnh từ văn bản và trả về dữ liệu bytes của ảnh."""
    try:
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        print(f"-> Generating image from text: '{prompt}'")
        
        image_generation_prompt = f"Generate a high-quality, photorealistic image with a {aspect_ratio} aspect ratio of: {prompt}"
        response = model.generate_content(image_generation_prompt, request_options={"timeout": 600})
        
        part = response.candidates[0].content.parts[0]
        if hasattr(part, 'inline_data') and part.inline_data.data:
            print("-> Image generated successfully from text.")
            return part.inline_data.data
        elif hasattr(part, 'text') and part.text:
            raise Exception(f"AI refused to generate image, saying: '{part.text}'")
        else:
            raise Exception("Image generation API did not return image data.")
            
    except Exception as e:
        print(f"-> Failed to generate image from text: {e}")
        raise e

def tao_video_tu_anh(image_bytes: bytes, prompt: str) -> dict:
    """Tải ảnh lên, tạo video từ ảnh đó, và trả về video dưới dạng base64."""
    try:
        print("-> Uploading image for video generation...")
        image_file_in_memory = io.BytesIO(image_bytes)
        image_file_in_memory.name = "temp_image_for_video.jpeg"
        uploaded_image = genai.upload_file(file_path=image_file_in_memory)
        print(f"-> Image uploaded. URI: {uploaded_image.uri}")
        
        print(f"-> Generating video from uploaded image with prompt: '{prompt}'")
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        
        generation_request = [prompt, uploaded_image]
        response = model.generate_content(generation_request, request_options={"timeout": 600})
        
        # Dọn dẹp file đã tải lên sau khi dùng xong
        genai.delete_file(uploaded_image.name)
        print(f"-> Cleaned up uploaded file: {uploaded_image.name}")

        video_part = response.candidates[0].content.parts[0]
        
        if hasattr(video_part, 'text') and video_part.text:
            raise Exception(f"AI refused to generate video, saying: '{video_part.text}'")
        elif hasattr(video_part, 'file_data') and video_part.file_data.uri:
            # Khi kết quả là video, API thường trả về một URI tham chiếu đến file
            video_file = genai.get_file(video_part.file_data.uri)
            video_base64 = base64.b64encode(video_file.blob).decode('utf-8')
            mime_type = video_file.mime_type
            print("-> Video created successfully.")
            return {"video_data": f"data:{mime_type};base64,{video_base64}"}
        else:
            raise Exception("Video generation API did not return a valid video file.")
            
    except Exception as e:
        print(f"-> Failed to generate video from image: {e}")
        raise e

# --- API ENDPOINT CHÍNH ---
@app.route('/generate-storyboard', methods=['POST'])
def handle_storyboard_generation():
    data = request.get_json()
    scenes = data.get('scenes', [])
    results = []
    
    print(f"\n--- NEW STORYBOARD REQUEST with {len(scenes)} scenes ---")
    
    for i, scene in enumerate(scenes):
        scene_number = i + 1
        prompt = scene.get('prompt', '')
        
        print(f"--- Processing Scene {scene_number}/{len(scenes)} ---")
        
        try:
            if scene.get('type') == 'text':
                aspect_ratio = scene.get('aspectRatio', '16:9')
                generated_image_bytes = tao_anh_tu_text(prompt, aspect_ratio)
                video_prompt = "Animate this image with subtle, cinematic movement."
                video_result = tao_video_tu_anh(generated_image_bytes, video_prompt)
            elif scene.get('type') == 'image':
                image_base64 = scene.get('content')
                if not image_base64: raise Exception("Image content is missing.")
                image_bytes = base64.b64decode(image_base64.split(',')[1])
                video_result = tao_video_tu_anh(image_bytes, prompt)
            else:
                raise Exception(f"Unknown scene type: {scene.get('type')}")

            results.append({ "scene_number": scene_number, "status": "success", "video_data": video_result["video_data"], "prompt": prompt })
            
        except Exception as e:
            results.append({ "scene_number": scene_number, "status": "failed", "error": str(e), "prompt": prompt })
            
    print("--- Storyboard processing finished ---\n")
    return jsonify({"results": results})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)