"""Food Verse AI backend. Run: uvicorn main:app --reload"""
import json, os, tempfile
import cv2, numpy as np
from google import genai
from google.genai import types
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

MODEL = os.getenv("MODEL", "gemini-2.5-flash")  # override with the MODEL env var
client = genai.Client()  # reads GEMINI_API_KEY from the environment
app = FastAPI(title="Food Verse AI")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def jpeg_bytes(img):
    """Preprocessing: cap size at 1024px, then JPEG-encode."""
    h, w = img.shape[:2]
    s = 1024 / max(h, w)
    if s < 1:
        img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    return cv2.imencode(".jpg", img)[1].tobytes()


async def read_image(f: UploadFile):
    img = cv2.imdecode(np.frombuffer(await f.read(), np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "That file isn't a readable image.")
    return jpeg_bytes(img)


def ask(prompt, images=(), max_tokens=1500):
    parts = [types.Part.from_bytes(data=b, mime_type="image/jpeg") for b in images]
    parts.append(prompt + "\nReply with one JSON object only.")
    try:
        r = client.models.generate_content(
            model=MODEL, contents=parts,
            config=types.GenerateContentConfig(response_mime_type="application/json", max_output_tokens=max_tokens * 2),
        )
        t = r.text or ""
        return json.loads(t[t.find("{"): t.rfind("}") + 1])
    except ValueError:
        raise HTTPException(502, "The model returned an unreadable answer. Try again.")
    except Exception as e:
        raise HTTPException(502, f"Model call failed: {e}")


@app.post("/food")
async def food(image: UploadFile = File(...), context: str = Form("")):
    return ask(
        f"Identify the dish in this photo. Extra context from the user: {context or 'none'}. JSON keys: dish, "
        "ingredients (list), portion_grams, calories, protein_g, carbs_g, fat_g, health_score (0-100 from macro "
        "balance and calorie density), confidence (0-1), insights (2 sentences), tips (list of improvements). "
        "All numbers are estimates.",
        [await read_image(image)],
    )


@app.post("/freshness")
async def freshness(image: UploadFile = File(...), storage_days: str = Form(""), storage_type: str = Form(""),
                    notes: str = Form("")):
    return ask(
        "Judge freshness from visible color, texture, discoloration, mold and surface patterns. User context: "
        f"stored {storage_days or '?'} days, storage {storage_type or '?'}, smell/texture notes: {notes or 'none'}. "
        'JSON keys: item, verdict (exactly "Fresh", "Moderately Fresh" or "Spoiled"), score (0-100, 100 = fresh), '
        "safe_to_eat (bool), confidence (0-1), signs (list of visible cues), recommendation. Be conservative: "
        "when unsure, lower confidence and advise caution.",
        [await read_image(image)],
    )


@app.post("/hygiene")
async def hygiene(video: UploadFile = File(...), rules: str = Form(""), frames: int = Form(6)):
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(await video.read())
    cap = cv2.VideoCapture(tmp.name)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    imgs, times = [], []
    for i in np.linspace(0, max(total - 1, 0), max(2, min(frames, 10))).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
        ok, frame = cap.read()
        if ok:
            imgs.append(jpeg_bytes(frame)); times.append(round(i / fps, 1))
    cap.release(); os.unlink(tmp.name)
    if not imgs:
        raise HTTPException(400, "Couldn't read any frames from that video.")
    return ask(
        f"Kitchen video frames at seconds {times}. Extra rules: {rules or 'none'}. Report only what is visible. "
        'JSON keys: score (0-100 compliance), indicators (list of {name, status ("ok"|"violation"|"unclear"), note}) '
        "covering gloves, hair cap, food handling, surface cleanliness; violations (list of {time_s, severity "
        '("low"|"medium"|"high"), issue}); summary.',
        imgs, 2000,
    )


@app.post("/cook")
async def cook(text: str = Form(""), diet: str = Form("none"), minutes: int = Form(30),
               image: UploadFile | None = File(None)):
    if not text and not image:
        raise HTTPException(400, "Describe a dish or ingredients, or upload a photo.")
    imgs = [await read_image(image)] if image else []
    return ask(
        f"Dish or ingredients: {text or 'see photo'}. Diet: {diet}. Time: {minutes} min. JSON keys: name, "
        "ingredients (list with quantities), missing_items (list), steps (ordered list of short instructions with "
        "technique cues like chop, heat, stir), tips (list).",
        imgs, 2000,
    )


@app.post("/plan")
async def plan(age: int = Form(...), sex: str = Form(...), height_cm: float = Form(...), weight_kg: float = Form(...),
               activity: float = Form(1.4), goal: str = Form("maintain"), diet: str = Form("none"),
               allergies: str = Form(""), conditions: str = Form(""), recent_meals: str = Form("")):
    if not (10 <= age <= 100 and 100 <= height_cm <= 230 and 25 <= weight_kg <= 250):
        raise HTTPException(422, "Check age, height and weight: one of them is outside a realistic range.")
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + (5 if sex == "male" else -161)  # Mifflin-St Jeor
    target = round(bmr * activity + {"lose": -400, "gain": 300}.get(goal, 0))
    out = ask(
        f"Create a day meal plan of about {target} kcal. Goal {goal}. Diet {diet}. Never include: "
        f"{allergies or 'no restrictions'}. Medical notes: {conditions or 'none'}. Recent meals to adapt to: "
        f"{recent_meals or 'none'}. JSON keys: health_score (0-100), protein_g (daily target), water_l, meals "
        "(list of {type, name, description, calories, protein_g, carbs_g, fat_g, alternative}), weekly (list of "
        "7 one-line day summaries), coach_tips (list).",
        max_tokens=3500,
    )
    return {"bmr": round(bmr), "target_calories": target, **out}
