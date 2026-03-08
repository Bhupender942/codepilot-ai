# CodePilot Groq Integration TODO

## Task Summary
Replace OpenRouter with Groq API using `llama-3.1-70b-versatile` model.

## Files Created

### 1. backend/app/services/llm_service.py ✅
- Created reusable Groq LLM service
- Uses Groq Python SDK
- Loads API key from environment variable GROQ_API_KEY
- Uses model: llama-3.1-70b-versatile
- Added error handling with fallback message
- Added 1 second delay between calls to prevent rate limits

### 2. backend/app/services/documentation_service.py ✅
- Reads repository files
- Filters important files using IGNORED_DIRS
- Splits code into chunks (150 lines for files > 200 lines)
- Sends each chunk to LLM
- Returns documentation

### 3. backend/app/routers/docs_router.py ✅
- Endpoint: POST /generate-docs
- Input: {"repo_url": "https://github.com/user/repo"}
- Process: Clone repo → Filter files → Chunk code → Send to Groq → Return documentation

## Files Updated

### 4. backend/requirements.txt ✅
Added:
```
groq
python-dotenv
```

### 5. backend/app/config.py ✅
- Updated groq_model default to "llama-3.1-70b-versatile"

### 6. backend/app/main.py ✅
- Imported and included the new docs_router

## Additional Files

### 7. backend/.env.example ✅
- Created example environment file with GROQ_API_KEY

## Implementation Details

### IGNORED_DIRS
```python
IGNORED_DIRS = [
    "node_modules",
    ".git",
    "build",
    "dist",
    "__pycache__",
    "venv"
]
```

### Chunking Logic
- Files > 200 lines: Split into chunks of 150 lines
- Uses time.sleep(1) between API calls

### Prompt Template
```
"You are a senior software engineer and teacher.

Explain the following code in simple English so that a beginner developer can understand it.

Return format:

Function Name:
Description:
Inputs:
Outputs:
Steps:
Time Complexity:
Space Complexity:"
```

## Status
- [x] Update requirements.txt
- [x] Update config.py
- [x] Create llm_service.py
- [x] Create documentation_service.py
- [x] Create docs_router.py
- [x] Update main.py
- [x] Create .env.example

## Setup Instructions

1. Install dependencies:
```bash
cd backend
pip install -r requirements.txt
```

2. Copy .env.example to .env and add your Groq API key:
```bash
cp .env.example .env
# Edit .env and set GROQ_API_KEY
```

3. Run the server:
```bash
uvicorn app.main:app --reload
```

4. Test the endpoint:
```bash
curl -X POST "http://localhost:8000/api/docs/generate-docs" \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/user/repo"}'
```

