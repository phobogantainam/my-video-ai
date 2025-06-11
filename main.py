import os
import json
import requests
import google.generativeai as genai
from dotenv import load_dotenv
from flask import Flask, request, jsonify

# --- PHẦN 1: CẤU HÌNH BAN ĐẦU ---

# Tải các biến môi trường từ file .env để Python có thể đọc được
load_dotenv()

# Lấy các API key từ biến môi trường đã tải
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
HAILOU_API_KEY = os.getenv("HAILOU_API_KEY")

# Cấu hình API Gemini
genai.configure(api_key=GOOGLE_API_KEY)
gemini_model = genai.GenerativeModel('gemini-pro')

# Điểm cuối API của Hailou (URL này là ví dụ, bạn cần thay bằng URL đúng từ tài liệu của họ)
HAILOU_TEXT_TO_IMAGE_URL = "https://api.minimax.io/v1/texttoimage" 
HAILOU_IMAGE_TO_VIDEO_URL = "https://api.minimax.io/v1/imagetovideo"

# Khởi tạo ứng dụng web Flask (khung của xưởng sản xuất)
app = Flask(__name__)

# --- PHẦN 2: CÁC HÀM CHỨC NĂNG CỦA DÂY CHUYỀN SẢN XUẤT ---

def tao_nhieu_prompt_chuyen_sau(y_tuong):
    print(f"Bắt đầu tạo nhiều prompt từ ý tưởng: '{y_tuong}'...")
    super_prompt = f"""Bạn là một Giám đốc Sáng tạo chuyên nghiệp, chuyên gia về AI tạo hình ảnh. Nhiệm vụ của bạn là nhận một ý tưởng đơn giản và phát triển nó thành một danh sách gồm 4 biến thể prompt chi tiết bằng tiếng Anh. Mỗi prompt phải độc đáo, khám phá một phong cách nghệ thuật hoặc một góc nhìn khác nhau. Yêu cầu cho mỗi prompt: 1. Cực kỳ chi tiết: Mô tả cảnh vật, nhân vật, hành động, cảm xúc. 2. Từ khóa chuyên nghiệp: Bao gồm các thuật ngữ về ánh sáng (ví dụ: cinematic lighting, volumetric light), phong cách (ví dụ: photorealistic, epic fantasy art, anime style, cyberpunk), chất lượng (ví dụ: 8K, ultra-detailed, sharp focus), và ống kính (ví dụ: wide-angle shot, close-up). 3. Đa dạng: Mỗi prompt phải khác biệt rõ rệt về phong cách hoặc nội dung. Hãy trả về kết quả dưới dạng một chuỗi JSON hợp lệ, là một danh sách của các đối tượng. Mỗi đối tượng trong danh sách phải có 2 key: "style" (một chuỗi ngắn mô tả phong cách) và "prompt" (chuỗi prompt chi tiết bằng tiếng Anh). Bây giờ, hãy thực hiện nhiệm vụ với ý tưởng sau đây: Ý tưởng: "{y_tuong}" """
    try:
        response = gemini_model.generate_content(super_prompt)
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        prompts = json.loads(cleaned_response)
        print(f"-> Đã tạo thành công {len(prompts)} biến thể prompt.")
        return prompts
    except Exception as e:
        print(f"Lỗi khi tạo và phân tích JSON từ Gemini: {e}")
        return None

def tao_hinh_anh_tu_prompt(prompt):
    print("  Đang gửi yêu cầu tạo ảnh đến Hailou AI...")
    headers = {"Authorization": f"Bearer {HAILOU_API_KEY}", "Content-Type": "application/json"}
    payload = {"prompt": prompt, "model": "MiniMax-Văn bản-01"} # Thay bằng model phù hợp
    response = requests.post(HAILOU_TEXT_TO_IMAGE_URL, json=payload, headers=headers)
    if response.status_code == 200:
        image_url = response.json().get("data")[0].get("url") 
        print(f"  -> Đã tạo ảnh thành công.")
        return image_url
    else:
        print(f"  Lỗi khi tạo ảnh: {response.text}")
        return None

def tao_video_tu_anh(image_url):
    print("    Đang gửi yêu cầu tạo chuyển động cho ảnh...")
    headers = {"Authorization": f"Bearer {HAILOU_API_KEY}", "Content-Type": "application/json"}
    payload = {"image_url": image_url}
    response = requests.post(HAILOU_IMAGE_TO_VIDEO_URL, json=payload, headers=headers)
    if response.status_code == 200:
        video_url = response.json().get("data")[0].get("url")
        print(f"    -> Đã tạo video thành công.")
        return video_url
    else:
        print(f"    Lỗi khi tạo video: {response.text}")
        return None

def chay_quy_trinh_hang_loat(y_tuong):
    danh_sach_prompts = tao_nhieu_prompt_chuyen_sau(y_tuong)
    if not danh_sach_prompts: return None
    ket_qua_cuoi_cung = []
    for i, item in enumerate(danh_sach_prompts):
        style, prompt = item.get("style"), item.get("prompt")
        print(f"\n--- Đang xử lý biến thể {i+1}/{len(danh_sach_prompts)}: Phong cách '{style}' ---")
        image_url = tao_hinh_anh_tu_prompt(prompt)
        if image_url:
            video_url = tao_video_tu_anh(image_url)
            if video_url:
                ket_qua_cuoi_cung.append({"style": style, "prompt": prompt, "video_url": video_url})
    return ket_qua_cuoi_cung

# --- PHẦN 3: CỔNG VÀO CỦA XƯỞNG SẢN XUẤT ---
# Đây là nơi nhận đơn đặt hàng từ Internet

@app.route('/create-multiple-videos', methods=['POST'])
def handle_multiple_video_creation():
    data = request.get_json()
    y_tuong = data.get('idea')
    if not y_tuong: return jsonify({"error": "Vui lòng nhập ý tưởng"}), 400
    try:
        results = chay_quy_trinh_hang_loat(y_tuong)
        if results: return jsonify({"results": results})
        else: return jsonify({"error": "Không thể tạo bất kỳ video nào"}), 500
    except Exception as e:
        return jsonify({"error": f"Lỗi hệ thống: {str(e)}"}), 500

# Dòng này chỉ dùng để chạy thử trên máy của bạn
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)