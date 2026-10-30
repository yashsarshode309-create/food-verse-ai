# FoodVerse AI: Multimodal Food Intelligence Platform

Analyze food through images, video and text: recognition and nutrition, freshness, kitchen hygiene, cooking guidance and personalized meal plans.

**Stack:** React (CDN) dashboard, FastAPI backend, OpenCV preprocessing, Gemini multimodal model.

## Modules
| Module | Endpoint | Output |
|---|---|---|
| Food Recognition | `POST /food` | dish, calories, macros, health score, tips |
| Freshness Detector | `POST /freshness` | Fresh / Moderately Fresh / Spoiled, safety flag, recommendation |
| Hygiene Monitor | `POST /hygiene` | compliance score, indicators, timestamped alerts |
| Smart Kitchen | `POST /cook` | recipe, ingredients, steps, tips |
| Meal Planner | `POST /plan` | calorie target (Mifflin-St Jeor), meals, weekly overview |

## Run locally
```
cd backend
python -m venv venv
venv\Scripts\activate        # Windows; use: source venv/bin/activate on Mac/Linux
pip install -r requirements.txt
set GEMINI_API_KEY=your_key    # use export on Mac/Linux
uvicorn main:app --reload
```
Then open `frontend/index.html` in a browser. Get a free key at https://aistudio.google.com/apikey. Never commit your key.

## Deploy
- **Backend (Render):** New Web Service from your GitHub repo, root directory `backend`, build command `pip install -r requirements.txt`, start command `uvicorn main:app --host 0.0.0.0 --port $PORT`, add environment variable `GEMINI_API_KEY`.
- **Frontend (Netlify / GitHub Pages):** set `API` at the top of `frontend/index.html` to your Render URL, then deploy the `frontend` folder.

## Limitations
Nutrition values are estimates. Freshness from a photo is a visual guess, not a lab test. Hygiene analysis samples a few frames and reports only what is visible.

## Screenshots
Add your screenshots to the `screenshots` folder and reference them here, for example:

![Food Recognition](screenshots/food-recognition.png)
![Freshness Detector](screenshots/freshness.png)
![Hygiene Monitor](screenshots/hygiene.png)
![Smart Kitchen](screenshots/smart-kitchen.png)
![Meal Planner](screenshots/meal-planner.png)
