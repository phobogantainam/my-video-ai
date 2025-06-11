import os
import json
import requests
import google.generativeai as genai
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS

# --- PART 1: INITIAL CONFIGURATION ---

# Load environment variables from .env file (only works when running locally)
load_dotenv()

# Get API keys from the ENVIRONMENT VARIABLES we set on Render
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
HAILOU_API_KEY = os.getenv("HAILOU_API_KEY")

# Configure Gemini API
genai.configure(api_key=GOOGLE_API_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-flash-latest')

# Hailou AI API Endpoints
HAILOU_TEXT_TO_IMAGE_URL = "https://api.minimax.io/v1/image_generation"
HAILOU_IMAGE_TO_VIDEO_URL = "https://api.minimax.io/v1/imagetovideo"

# Initialize Flask web application
app = Flask(__name__)
CORS(app) # Allow other websites to call this API

# --- PART 2: CORE APPLICATION FUNCTIONS ---

def tao_nhieu_prompt_chuyen_sau(y_tuong):
    print(f"1. Using Gemini to generate prompts from idea: '{y_tuong}'...")
    super_prompt = f"""You are a creative director and an expert in AI image generation. Your task is to take a simple idea and expand it into a list of 2 detailed and diverse prompts in English. Each prompt must be unique, exploring different art styles, perspectives, or moods. Requirements for each prompt: 1. Extremely detailed: Describe the scene, characters, actions, and emotions. 2. Professional keywords: Include terms for lighting (e.g., cinematic lighting, volumetric light), style (e.g., photorealistic, epic fantasy art, anime style, cyberpunk), quality (e.g., 8K, ultra-detailed, sharp focus), and camera lenses (e.g., wide-angle shot, close-up). 3. Diverse: Each prompt should be distinctly different in style or content. Return the result as a valid JSON array of objects. Each object must have two keys: "style" (a short string describing the style) and "prompt" (the detailed English prompt). Now, perform the task for the following idea: Idea: "{y_tuong}" """
    try:
        response = gemini_model.generate_content(super_prompt)
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        prompts = json.loads(cleaned_response)
        print(f"-> Successfully generated {len(prompts)} prompt variants.")
        return prompts
    except Exception as e:
        print(f"Error generating or parsing JSON from Gemini: {e}")
        return None

# HÀM TẠO ẢNH ĐÃ NÂNG CẤP
def tao_hinh_anh_tu_prompt(prompt):
    print("2. Sending image generation request to Hailou AI...")
    headers = {"Authorization": f"Bearer {HAILOU_API_KEY}", "Content-Type": "application/json"}
    payload = {"prompt": prompt, "model": "image-01"}
    response = requests.post(HAILOU_TEXT_TO_IMAGE_URL, json=payload, headers=headers)

    json_response = response.json()
    print(f"Hailou Image Response JSON: {json_response}")

    if response.status_code == 200:
        data_list = json_response.get("data")
        if data_list and len(data_list) > 0:
            image_url = data_list[0].get("url")
            print("-> Image created successfully.")
            return image_url
        else:
            error_message = json_response.get('base_resp', {}).get('status_msg', 'Unknown error from Hailou.')
            print(f"-> Error from Hailou API: {error_message}")
            return None
    else:
        print(f"-> HTTP Error creating image: {response.text}")
        return None

# HÀM TẠO VIDEO ĐÃ NÂNG CẤP
def tao_video_tu_anh(image_url):
    print("3. Sending image animation request to Hailou AI...")
    headers = {"Authorization": f"Bearer {HAILOU_API_KEY}", "Content-Type": "application/json"}
    payload = {"image_url": image_url}
    response = requests.post(HAILOU_IMAGE_TO_VIDEO_URL, json=payload, headers=headers)

    json_response = response.json()
    print(f"Hailou Video Response JSON: {json_response}")

    if response.status_code == 200:
        data_list = json_response.get("data")
        if data_list and len(data_list) > 0:
            video_url = data_list[0].get("url")
            print("-> Video created successfully.")
            return video_url
        else:
            error_message = json_response.get('base_resp', {}).get('status_msg', 'Unknown error from Hailou.')
            print(f"-> Error from Hailou API: {error_message}")
            return None
    else:
        print(f"-> HTTP Error creating video: {response.text}")
        return None

def chay_quy_trinh_hang_loat(y_tuong):
    danh_sach_prompts = tao_nhieu_prompt_chuyen_sau(y_tuong)
    if not danh_sach_prompts: return None
    ket_qua_cuoi_cung = []
    for i, item in enumerate(danh_sach_prompts):
        style, prompt = item.get("style"), item.get("prompt")
        print(f"\n--- Processing variant {i+1}/{len(danh_sach_prompts)}: Style '{style}' ---")
        image_url = tao_hinh_anh_tu_prompt(prompt)
        if image_url:
            video_url = tao_video_tu_anh(image_url)
            if video_url:
                ket_qua_cuoi_cung.append({"style": style, "prompt": prompt, "video_url": video_url})
    return ket_qua_cuoi_cung

# --- PART 3: API ENDPOINT ---
# This is the "door" that receives requests from the internet

@app.route('/create-multiple-videos', methods=['POST'])
def handle_multiple_video_creation():
    data = request.get_json()
    y_tuong = data.get('idea')
    if not y_tuong: return jsonify({"error": "Please provide an idea"}), 400
    try:
        results = chay_quy_trinh_hang_loat(y_tuong)
        if results: return jsonify({"results": results})
        else: return jsonify({"error": "Could not create any video"}), 500
    except Exception as e:
        return jsonify({"error": f"System error: {str(e)}"}), 500

# This line is only for testing on your own computer
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
