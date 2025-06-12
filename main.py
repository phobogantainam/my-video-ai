import os
import base64
import io
import time # Thêm dòng này
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

# --- CÁC HÀM LÕI ---

def tao_anh_tu_text(prompt: str, aspect_ratio: str) -> bytes:
    """Sử dụng AI để tạo ảnh từ văn bản và trả về dữ liệu bytes của ảnh."""
    try:
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        print(f"-> Generating image from text with aspect ratio {aspect_ratio}: '{prompt}'")
        image_generation_prompt = f"Generate a high-quality, photorealistic image with a {aspect_ratio} aspect ratio of: {prompt}"
        response = model.generate_content(image_generation_prompt, request_options={"timeout": 600})
        
        part = response.candidates[0].content.parts[0]
        if hasattr(part, 'inline_data') and part.inline_data.data:
            print("-> Image generated successfully from text.")
            return part.inline_data.data
        elif hasattr(part, 'text') and part.text:
            raise Exception(f"AI refused to generate image: {part.text}")
        else:
            raise Exception("Image generation API did not return image data.")
            
    except Exception as e:
        print(f"-> Failed to generate image: {e}")
        raise e

def tao_video_tu_anh(image_bytes: bytes, prompt: str) -> dict:
    """
    PHIÊN BẢN DEMO: Luôn trả về một video mẫu có sẵn, không gọi API tốn phí.
    """
    print("-> DEMO MODE: Skipping paid video generation API call.")
    print("-> Returning a sample placeholder video.")
    
    # Dữ liệu của một video MP4 mẫu rất ngắn đã được mã hóa base64
    sample_video_base64 = "AAAAGGZ0eXAzZ3A0AAAAAGlzb20zZ3A0AAAAAWRtZGF0AAAAAAAAAAAAAAACLG1kYXQAAAMrK//VideoDataPlaceholderForDemo//jL//AABHAAADAAEFAAAA"
    mime_type = "video/mp4"
    
    # Giả lập một chút độ trễ để giống thật hơn
    time.sleep(5) # Chờ 5 giây

    print("-> Demo video returned successfully.")
    return {"video_data": f"data:{mime_type};base64,{sample_video_base64}", "status": "success"}

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
            # Quy trình Text -> Image -> Video
            if scene.get('type') == 'text':
                aspect_ratio = scene.get('aspectRatio', '16:9')
                generated_image_bytes = tao_anh_tu_text(prompt, aspect_ratio)
                video_prompt = "Animate this image with subtle, cinematic movement."
                video_result = tao_video_tu_anh(generated_image_bytes, video_prompt)
            # Quy trình Image -> Video
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
