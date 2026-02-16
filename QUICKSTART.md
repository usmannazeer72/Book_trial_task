# Quick Start Guide

## Prerequisites

- Python 3.11+
- MongoDB installed locally or MongoDB Atlas account
  -- Groq API key (set `GROQ_API_KEY` in your `.env`)

## 5-Minute Setup

### Step 1: Clone and Setup Environment

```bash
cd Book_trial_task
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` file with minimum required values:

```env
GROQ_API_KEY=your_actual_groq_api_key_here
GROQ_MODEL=chat-bison-001
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE=book_generation
```

### Step 3: Start MongoDB

```bash
# If using local MongoDB
mongod

# OR use Docker
docker run -d -p 27017:27017 --name mongodb mongo:7.0
```

### Step 4: Initialize System

```bash
python main.py init
```

### Step 5: Create Sample Data

```bash
python create_sample_input.py
```

This creates `input/books_input.xlsx` with 3 sample books.

### Step 6: Run the System

```bash
python main.py run
```

**First Run Output:**

- ✓ Ingests 3 books from Excel
- ✓ Generates 3 outlines
- ⏸️ Pauses - waiting for editor approval

### Step 7: Approve an Outline (Manual Step)

Option A - Using MongoDB Compass/Shell:

```javascript
// Connect to: mongodb://localhost:27017/book_generation
db.books.updateOne(
  { title: "The Future of Artificial Intelligence" },
  { $set: { status_outline_notes: "no_notes_needed" } },
);
```

Option B - Using Python:

```python
from pymongo import MongoClient
client = MongoClient('mongodb://localhost:27017/')
db = client['book_generation']
db.books.update_one(
    {'title': 'The Future of Artificial Intelligence'},
    {'$set': {'status_outline_notes': 'no_notes_needed'}}
)
```

### Step 8: Generate Chapters

```bash
python main.py run
```

**Second Run Output:**

- ✓ Generates chapters for approved book
- ⏸️ Pauses - waiting for chapter approval

### Step 9: Approve Chapters

```javascript
// Approve each chapter
db.chapters.updateMany(
  { book_id: "your_book_id_here" },
  { $set: { chapter_notes_status: "no_notes_needed" } },
);
```

### Step 10: Final Compilation

```javascript
// Allow final compilation
db.books.updateOne(
  { title: "The Future of Artificial Intelligence" },
  { $set: { final_review_notes_status: "no_notes_needed" } },
);
```

```bash
python main.py run
```

**Third Run Output:**

- ✓ Compiles final book
- ✓ Generates DOCX, PDF, TXT in `output/` folder
- ✓ Sends completion notification (if email configured)

## Verify Output

Check the `output/` directory:

```bash
dir output  # Windows
ls output   # Linux/Mac
```

You should see:

- `The_Future_of_Artificial_Intelligence_xxxxx.docx`
- `The_Future_of_Artificial_Intelligence_xxxxx.pdf`
- `The_Future_of_Artificial_Intelligence_xxxxx.txt`

## Using Docker (Alternative)

```bash
# Create .env file with your API keys
cp .env.example .env
# Edit .env

# Start everything
docker-compose up -d

# View logs
docker-compose logs -f book_generator

# Stop
docker-compose down
```

## Troubleshooting

**MongoDB Connection Error:**

```bash
# Check if MongoDB is running
mongod --version

# Or use Docker
docker ps | grep mongo
```

**Groq API Error:**

- Verify `GROQ_API_KEY` is correct in `.env`
- Check quota and model availability on your Groq dashboard

**No Books Ingested:**

- Verify `input/books_input.xlsx` exists
- Check Excel file has required columns: `title`, `notes_on_outline_before`

## Next Steps

1. **Customize Input:** Edit `input/books_input.xlsx` with your own books
2. **Configure Notifications:** Add SMTP credentials to `.env` for email notifications
3. **Add More Books:** Keep adding rows to Excel and run `python main.py run`
4. **Review Workflow:** Check MongoDB to see the complete state

## Full Workflow Status Check

```python
# View all books and their status
from pymongo import MongoClient
client = MongoClient('mongodb://localhost:27017/')
db = client['book_generation']

for book in db.books.find():
    print(f"\nBook: {book['title']}")
    print(f"  Outline Status: {book.get('status_outline_notes', 'pending')}")
    print(f"  Output Status: {book.get('book_output_status', 'pending')}")

    chapters = db.chapters.count_documents({'book_id': book['book_id']})
    print(f"  Chapters: {chapters}")
```

## Key Commands

```bash
# Initialize database
python main.py init

# Run complete workflow
python main.py run

# Process single book
python main.py run-book --book-id <book_id>

# Run tests
pytest tests/ -v

# Create sample input
python create_sample_input.py
```

## Support

- 📖 Full docs: [README.md](README.md)
- 🏗️ Architecture: [ARCHITECTURE.md](ARCHITECTURE.md)
- 📝 Implementation: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
