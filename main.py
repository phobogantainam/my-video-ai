import os
import base64
import io
import google.generativeai as genai
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS

# --- CẤU HÌNH BAN ĐẦU ---
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# --- KHỞI TẠO ỨNG DỤNG WEB ---
app = Flask(__name__)
CORS(app)

# --- CÁC HÀM LÕI ---

def tao_anh_tu_text(prompt: str, aspect_ratio: str = "16:9") -> bytes:
    """Sử dụng AI để tạo ảnh từ văn bản và trả về dữ liệu bytes của ảnh."""
    try:
        print(f"-> Generating image from text with aspect ratio {aspect_ratio}: '{prompt}'")
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        
        # Thêm chỉ thị về tỷ lệ vào trong prompt để AI hiểu
        image_generation_prompt = f"Generate a high-quality, photorealistic image with a {aspect_ratio} aspect ratio of: {prompt}"
        
        response = model.generate_content(image_generation_prompt, request_options={"timeout": 600})
        
        image_part = response.candidates[0].content.parts[0]
        if hasattr(image_part, 'inline_data') and hasattr(image_part.inline_data, 'data'):
            image_bytes = image_part.inline_data.data
            print("-> Image generated successfully.")
            return image_bytes
        elif hasattr(image_part, 'text') and image_part.text:
            raise Exception(f"AI refused to generate image: {image_part.text}")
        else:
            raise Exception("Image generation did not return valid image data.")
            
    except Exception as e:
        print(f"-> Failed to generate image: {e}")
        raise e

def tao_video_tu_anh(image_bytes: bytes, prompt: str) -> dict:
    """Sử dụng AI để tạo video từ dữ liệu ảnh (bytes) và trả về video dưới dạng base64."""
    try:
        print(f"-> Generating video from image with prompt: '{prompt}'")
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        
        image_part = {"mime_type": "image/jpeg", "data": image_bytes}
        generation_request = [prompt, image_part]
        
        response = model.generate_content(generation_request, request_options={"timeout": 600})
        video_part = response.candidates[0].content.parts[0]
        
        if hasattr(video_part, 'text') and video_part.text:
            raise Exception(f"AI refused to generate video: {video_part.text}")
        elif hasattr(video_part, 'inline_data') and hasattr(video_part.inline_data, 'data'):
            video_base64 = base64.b64encode(video_part.inline_data.data).decode('utf-8')
            mime_type = video_part.inline_data.mime_type
            print("-> Video created successfully.")
            return {"video_data": f"data:{mime_type};base64,{video_base64}", "status": "success"}
        else:
            raise Exception("Received an unknown or empty response from video generation API.")
            
    except Exception as e:
        print(f"-> Failed to generate video: {e}")
        raise e

# --- API ENDPOINT CHÍNH ---
@app.route('/generate-storyboard', methods=['POST'])
def handle_storyboard_generation():
    data = request.get_json()
    if not data or 'scenes' not in data or not isinstance(data['scenes'], list):
        return jsonify({"error": "Invalid request. 'scenes' field must be a list."}), 400

    scenes = data['scenes']
    results = []
    
    print(f"--- Starting new storyboard processing with {len(scenes)} scenes ---")
    
    for i, scene in enumerate(scenes):
        scene_number = i + 1
        scene_type = scene.get('type')
        prompt = scene.get('prompt')
        
        print(f"\n--- Processing Scene {scene_number}/{len(scenes)} ---")
        
        try:
            # Quy trình Text -> Image -> Video
            if scene_type == 'text':
                aspect_ratio = scene.get('aspectRatio', '16:9')
                generated_image_bytes = tao_anh_tu_text(prompt, aspect_ratio)
                video_prompt = "Animate this image with subtle, cinematic movement."
                video_result = tao_video_tu_anh(generated_image_bytes, video_prompt)
            # Quy trình Image -> Video
            elif scene_type == 'image':
                image_base64 = scene.get('content')
                if not image_base64: raise Exception("Image content is missing.")
                image_bytes = base64.b64decode(image_base64.split(',')[1])
                video_result = tao_video_tu_anh(image_bytes, prompt)
            else:
                raise Exception(f"Unknown scene type: {scene_type}")

            results.append({ "scene_number": scene_number, "status": "success", "video_data": video_result["video_data"], "prompt": prompt })
            
        except Exception as e:
            results.append({ "scene_number": scene_number, "status": "failed", "error": str(e), "prompt": prompt })
            
    print("--- Storyboard processing finished ---")
    return jsonify({"results": results})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)