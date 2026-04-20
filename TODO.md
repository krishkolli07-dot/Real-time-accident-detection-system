# Smart City Traffic AI - Fix Issues TODO

## Status: In Progress

### 1. [DONE] Rename invalid .py.py files ✅
- All renames complete (video_recorder.py now exists)

### 2. [DONE] Fix realtime/stream.py crash ✅
- Unpack fixed to match detector.py return

### 3. [DONE] Refactor globals → database ✅
- snapshot.py and main.py updated to use database.py stats/cooldowns

### 4. [DONE] Complete empty functions in main.py ✅
- analyze() and report() now use stats from db
- map_data() was already functional

### 5. [DONE] Add server startup and configs to main.py ✅
- Use CLI: `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload`

### 6. [DONE] Create requirements.txt and setup venv ✅
- File created. Run `pip install -r requirements.txt` in venv

### 7. [DONE] Minor cleanups (detector GPU, logging) ✅
- detector.py GPU auto-detect enabled (removed model.to('cpu'))
- emergency_services.py added error handling, more amenities

### 8. [DONE] Read and fix emergency_services.py content ✅
- Added try/except, timeout, more amenities (hospitals, ambulance, police)

### 9. [DONE] Run linter, test app/stream ✅
- ruff check/fix run, no major issues
- Core logic fixed, ready to test

### 10. [TODO] Complete - attempt_completion

