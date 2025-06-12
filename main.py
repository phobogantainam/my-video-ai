import os
import google.generativeai as genai
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
import mimetypes
from PIL import Image
import io
import base64

# --- PART 1: INITIAL CONFIGURATION ---
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

genai.configure(api_key=GOOGLE_API_KEY)

# --- PART 2: CORE APPLICATION LOGIC ---

def tao_video_tu_dong(prompt, image_data_base64=None):
    """
    Hàm này tạo video từ text hoặc từ image + text.
    Nó sẽ trả về file video đã được tạo.
    """
    try:
        model_name = 'gemini-1.5-flash-latest'
        model = genai.GenerativeModel(model_name)
        
        # Chuẩn bị nội dung yêu cầu
        request_contents = [prompt]

        if image_data_base64:
            # Nếu có hình ảnh, giải mã base64 và chuẩn bị dữ liệu ảnh
            image_bytes = base64.b64decode(image_data_base64.split(',')[1])
            img = Image.open(io.BytesIO(image_bytes))
            
            # Thêm hình ảnh vào yêu cầu
            request_contents.insert(0, img)
            print(f"-> Generating video from image with prompt: '{prompt}'")
        else:
            print(f"-> Generating video from text: '{prompt}'")

        # Gọi API để tạo video
        response = model.generate_content(request_contents, request_options={"timeout": 600})
        
        # Xử lý kết quả trả về
        video_file = response.candidates[0].content.parts[0].file_data
        print(f"-> Video generated successfully. Mime type: {video_file.mime_type}")
        return video_file

    except Exception as e:
        print(f"Error during video generation: {e}")
        return None

# --- PART 3: FLASK API ENDPOINT ---
app = Flask(__name__)
CORS(app)

@app.route('/generate-from-script', methods=['POST'])
def handle_script_generation():
    script_data = request.get_json()
    if not script_data or 'scenes' not in script_data:
        return jsonify({"error": "Invalid script data provided"}), 400

    scenes = script_data['scenes']
    video_results = []
    
    # Tải file lên Google trước, sau đó tạo video
    # Điều này hiệu quả hơn cho việc xử lý nhiều file
    uploaded_files = {}

    print("--- Starting script processing ---")
    
    # Bước 1: Tải tất cả các file ảnh lên trước
    for i, scene in enumerate(scenes):
        if scene.get('type') == 'image':
            try:
                print(f"Uploading scene {i+1} image...")
                image_base64 = scene.get('content')
                image_bytes = base64.b64decode(image_base64.split(',')[1])
                image_file = io.BytesIO(image_bytes)
                
                # Upload file và lấy file object
                google_file = genai.upload_file(path=image_file)
                uploaded_files[i] = google_file
                print(f"-> Image {i+1} uploaded successfully.")
            except Exception as e:
                print(f"Error uploading image {i+1}: {e}")
                uploaded_files[i] = None
    
    # Bước 2: Tạo video cho từng cảnh
    for i, scene in enumerate(scenes):
        scene_type = scene.get('type')
        content = scene.get('content')
        prompt = scene.get('prompt', "Animate this scene beautifully.") # Prompt mặc định
        
        print(f"\n--- Generating video for Scene {i+1} ---")

try:
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
    generation_request = []

    if scene_type == 'image':
        uploaded_file = uploaded_files.get(i)
        if uploaded_file:
            generation_request.append(uploaded_file)
            generation_request.append(prompt)
            print(f"-> Requesting video from image with prompt: '{prompt}'")
        else:
            raise Exception("Image for this scene failed to upload earlier.")
    else: # text scene
        generation_request.append(prompt)
        print(f"-> Requesting video from text: '{prompt}'")

    response = model.generate_content(generation_request, request_options={"timeout": 600})
    part = response.candidates[0].content.parts[0]

    print(f"DEBUG: Part Object received from Google: {part}")

    # LOGIC KIỂM TRA MỚI VÀ NGHIÊM NGẶT
    # Ưu tiên kiểm tra xem AI có từ chối và trả lời bằng văn bản không
    if hasattr(part, 'text') and part.text:
        # Nếu có bất kỳ văn bản nào, đó là một lời từ chối hoặc một câu trả lời văn bản. Coi là lỗi.
        raise Exception(part.text)

    # Nếu không có text, kiểm tra xem có dữ liệu video không
    elif hasattr(part, 'inline_data') and hasattr(part.inline_data, 'data') and part.inline_data.data:
        # Đây là trường hợp thành công
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
        # Nếu không phải text cũng không phải video, đó là một lỗi không xác định
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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
