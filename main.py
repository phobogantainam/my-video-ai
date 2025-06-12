import os
import base64
import io
import google.generativeai as genai
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS

# --- PART 1: INITIAL CONFIGURATION ---
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# --- PART 2: FLASK APP INITIALIZATION ---
app = Flask(__name__)
CORS(app)

# --- PART 3: API ENDPOINT AND LOGIC ---

@app.route('/generate-from-script', methods=['POST'])
def handle_script_generation():
    script_data = request.get_json()
    if not script_data or 'scenes' not in script_data:
        return jsonify({"error": "Invalid script data provided"}), 400

    scenes = script_data['scenes']
    video_results = []
    
    print("--- Starting script processing ---")
    
    # Lặp qua từng cảnh để tạo video
    for i, scene in enumerate(scenes):
        scene_type = scene.get('type')
        # Lấy prompt của người dùng, nếu không có thì dùng prompt mặc định
        prompt = scene.get('prompt')
        if not prompt:
            if scene_type == 'image':
                prompt = "Animate this image with dynamic movement."
            else:
                prompt = scene.get('content', 'A beautiful video.')

        scene_number = i + 1
        
        print(f"\n--- Generating video for Scene {scene_number} ---")
        
        try:
            model = genai.GenerativeModel('gemini-1.5-pro-latest')
            generation_request = []

            # Xử lý cho cảnh là hình ảnh
            if scene_type == 'image':
                image_base64 = scene.get('content')
                if not image_base64:
                    raise Exception("Image scene provided but no image data found.")
                
                # Thêm prompt và hình ảnh vào yêu cầu
                generation_request.append(prompt)
                # Decode the base64 string to bytes
                image_bytes = base64.b64decode(image_base64.split(',')[1])
                # Create an image object for the library
                image_part = {"mime_type": "image/jpeg", "data": image_bytes}
                generation_request.append(image_part)
                print(f"-> Requesting video from image with prompt: '{prompt}'")
            
            # Xử lý cho cảnh là văn bản
            else:
                generation_request.append(prompt)
                print(f"-> Requesting video from text: '{prompt}'")
            
            # Gọi API của Google
            response = model.generate_content(generation_request, request_options={"timeout": 600})
            part = response.candidates[0].content.parts[0]
            
            print(f"DEBUG: Part Object received from Google: {part}")

            # LOGIC KIỂM TRA MỚI VÀ NGHIÊM NGẶT
            if hasattr(part, 'text') and part.text:
                raise Exception(part.text)
            elif hasattr(part, 'inline_data') and hasattr(part.inline_data, 'data') and part.inline_data.data:
                video_base64 = base64.b64encode(part.inline_data.data).decode('utf-8')
                mime_type = part.inline_data.mime_type
                video_results.append({
                    "scene_number": scene_number,
                    "status": "success",
                    "video_data": f"data:{mime_type};base64,{video_base64}",
                    "prompt": prompt
                })
                print(f"-> Video for scene {scene_number} created successfully.")
            else:
                raise Exception("Received an unknown or empty response from Google AI.")

        except Exception as e:
            print(f"-> Failed to generate video for scene {scene_number}: {e}")
            video_results.append({
                "scene_number": scene_number,
                "status": "failed",
                "error": str(e),
                "prompt": prompt
            })
    
    print("--- Script processing finished ---")
    return jsonify({"results": video_results})

# Dòng này chỉ dùng để chạy thử trên máy của bạn
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
