# Automated Book Generation System

A modular, scalable system for automated book generation using AI (Gemini API), with human-in-the-loop review at every stage.

## 🏗️ Architecture Overview

```
Input (Excel/Sheets) → Ingestion → MongoDB → Outline Generation →
Chapter Generation (with context chaining) → Compilation → PDF/DOCX/TXT Output
                                    ↓
                            Notifications (Email/Teams)
```

## 🛠️ Technology Stack

| Component            | Technology                                  |
| -------------------- | ------------------------------------------- |
| **Backend**          | Python 3.11+                                |
| **Database**         | MongoDB                                     |
| **LLM API**          | Google Gemini API                           |
| **Input**            | Google Sheets API / Excel (pandas)          |
| **Output**           | .docx (python-docx), .pdf (ReportLab), .txt |
| **Notifications**    | SMTP Email, MS Teams Webhooks               |
| **Containerization** | Docker, Docker Compose                      |

## 📋 Features

### 1. **Multi-Stage Workflow with Gating Logic**

- **Stage 1: Outline Generation**
  - Input validation (requires `notes_on_outline_before`)
  - Editor review with `status_outline_notes` (yes/no/no_notes_needed)
  - Regeneration support with feedback

- **Stage 2: Chapter Generation**
  - Sequential chapter generation with context chaining
  - Previous chapter summaries used as context for next chapter
  - Per-chapter review and regeneration
  - Gating based on `chapter_notes_status`

- **Stage 3: Final Compilation**
  - Compile to multiple formats (.docx, .pdf, .txt)
  - Final review gating with `final_review_notes_status`
  - Automatic storage and notification

### 2. **Context Chaining**

Each chapter is generated with awareness of previous chapters:

- Summaries of chapters 1 to N-1 are fed as context when generating chapter N
- Ensures narrative consistency and avoids repetition
- Summaries stored in MongoDB for reuse

### 3. **Human-in-the-Loop Review**

- Editor can add notes at every stage
- Flexible status flags control workflow progression
- Pause/resume capability
- Regeneration with feedback

### 4. **Notification System**

Automated notifications via:

- **Email (SMTP)** - Outline ready, chapter ready, book completed, errors
- **MS Teams Webhooks** - Real-time updates to team channels

### 5. **Modular Design**

- Separate services for ingestion, outline generation, chapter generation, compilation
- Easy to extend or replace individual components
- Database-driven state management

## 📂 Project Structure

```
Book_trial_task/
├── src/
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py              # Configuration management
│   ├── database/
│   │   ├── __init__.py
│   │   └── schema.py                # MongoDB schema and utils
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ingestion_service.py     # Excel/Sheets ingestion
│   │   ├── llm_service.py           # Gemini API integration
│   │   ├── notification_service.py  # Email/Teams notifications
│   │   ├── outline_generator.py     # Outline generation with gating
│   │   ├── chapter_generator.py     # Chapter generation with context
│   │   └── compilation_service.py   # Final document compilation
│   ├── __init__.py
│   └── orchestrator.py              # Main workflow orchestrator
├── input/
│   └── books_input.xlsx             # Sample input file
├── output/                          # Generated books (DOCX/PDF/TXT)
├── main.py                          # CLI entry point
├── create_sample_input.py           # Create sample Excel file
├── requirements.txt                 # Python dependencies
├── Dockerfile                       # Docker configuration
├── docker-compose.yml               # Docker Compose setup
├── .env.example                     # Environment variables template
├── .gitignore
├── ARCHITECTURE.md                  # Detailed architecture documentation
└── README.md                        # This file
```

## 🚀 Setup & Installation

### Prerequisites

- Python 3.11+
- MongoDB (local or Atlas)
- Google Gemini API key
- (Optional) Google Sheets API credentials
- (Optional) SMTP credentials for email notifications

### Local Installation

1. **Clone the repository**

```bash
git clone <repository_url>
cd Book_trial_task
```

2. **Create virtual environment**

```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure environment**

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```env
GEMINI_API_KEY=your_gemini_api_key
MONGODB_URI=mongodb://localhost:27017/
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
# ... etc
```

5. **Start MongoDB** (if running locally)

```bash
mongod
```

6. **Initialize database**

```bash
python main.py init
```

7. **Create sample input file**

```bash
python create_sample_input.py
```

### Docker Installation

1. **Configure environment**

```bash
cp .env.example .env
# Edit .env with your API keys
```

2. **Run with Docker Compose**

```bash
docker-compose up -d
```

This will start:

- MongoDB container
- Book Generation application container

## 📖 Usage

### Command Line Interface

**Initialize database:**

```bash
python main.py init
```

**Run complete workflow (Excel input):**

```bash
python main.py run --input-source excel --excel-path input/books_input.xlsx
```

**Run complete workflow (Google Sheets):**

```bash
python main.py run --input-source sheets
```

**Process single book:**

```bash
python main.py run-book --book-id <book_id>
```

### Workflow Steps

#### 1. Prepare Input Data

Create an Excel file (`input/books_input.xlsx`) with columns:

- `title` - Book title (required)
- `notes_on_outline_before` - Requirements for outline generation (required)
- `notes_on_outline_after` - Feedback on generated outline (optional)
- `status_outline_notes` - Status: "", "yes", "no", "no_notes_needed"

#### 2. Run Ingestion

```bash
python main.py run
```

This will:

- Ingest books from Excel/Sheets
- Generate outlines (where notes_on_outline_before exists)
- Send notification to editor

#### 3. Editor Reviews Outline

In MongoDB, update the book record:

```javascript
db.books.updateOne(
  { book_id: "xxx" },
  { $set: { status_outline_notes: "no_notes_needed" } },
);
```

Or, to request changes:

```javascript
db.books.updateOne(
  { book_id: "xxx" },
  {
    $set: {
      status_outline_notes: "yes",
      notes_on_outline_after: "Add more focus on X...",
    },
  },
);
```

#### 4. Generate Chapters

Run workflow again:

```bash
python main.py run
```

Chapters will be generated sequentially with context from previous chapters.

#### 5. Review Chapters

For each chapter, update status:

```javascript
db.chapters.updateOne(
  { book_id: "xxx", chapter_number: 1 },
  { $set: { chapter_notes_status: "no_notes_needed" } },
);
```

#### 6. Compile Final Book

When all chapters are approved:

```javascript
db.books.updateOne(
  { book_id: "xxx" },
  { $set: { final_review_notes_status: "no_notes_needed" } },
);
```

Run workflow:

```bash
python main.py run
```

Final book will be compiled to `output/` folder in DOCX, PDF, and TXT formats.

## 🔄 Gating Logic

### Outline Stage

- ✅ Generate: `notes_on_outline_before` exists AND `status_outline_notes` is empty/pending
- ⏸️ Pause: `status_outline_notes` == "no" or "yes" (waiting for notes)
- ➡️ Proceed: `status_outline_notes` == "no_notes_needed"

### Chapter Stage

- ✅ Generate: Outline approved AND previous chapter approved/pending
- ⏸️ Pause: `chapter_notes_status` == "no" or "yes" (waiting for notes)
- ➡️ Proceed: `chapter_notes_status` == "no_notes_needed"

### Compilation Stage

- ✅ Compile: All chapters approved AND `final_review_notes_status` allows
- ⏸️ Pause: `final_review_notes_status` == "no"
- ➡️ Proceed: `final_review_notes_status` == "no_notes_needed" or "yes"

## 📊 MongoDB Schema

### Collections

**books**

```javascript
{
  _id: ObjectId,
  book_id: String,
  title: String,
  notes_on_outline_before: String,
  notes_on_outline_after: String,
  status_outline_notes: String,  // "", "yes", "no", "no_notes_needed"
  final_review_notes_status: String,
  book_output_status: String,  // "pending", "in_progress", "completed"
  created_at: DateTime,
  updated_at: DateTime
}
```

**outlines**

```javascript
{
  _id: ObjectId,
  book_id: String,
  outline_text: String,
  version: Number,
  created_at: DateTime
}
```

**chapters**

```javascript
{
  _id: ObjectId,
  book_id: String,
  chapter_number: Number,
  chapter_title: String,
  content: String,
  chapter_notes_status: String,
  chapter_notes: String,
  created_at: DateTime,
  updated_at: DateTime
}
```

**chapter_summaries**

```javascript
{
  _id: ObjectId,
  chapter_id: String,
  book_id: String,
  summary_text: String,
  created_at: DateTime
}
```

## 🔔 Notification Events

1. **Outline Ready** - When outline is generated and needs review
2. **Chapter Ready** - When each chapter is generated
3. **Book Completed** - When final compilation is done
4. **Errors** - When workflow pauses due to errors or missing input

## 🧪 Testing

Run individual services:

```bash
# Test ingestion
python -m src.services.ingestion_service

# Test outline generation
python -m src.services.outline_generator

# Test chapter generation
python -m src.services.chapter_generator

# Test compilation
python -m src.services.compilation_service
```

## 🔧 Advanced Configuration

### Custom LLM Prompts

Edit `src/services/llm_service.py` to customize prompts for:

- Outline generation
- Chapter generation
- Summary generation

### Custom Output Formats

Extend `src/services/compilation_service.py` to add:

- HTML output
- EPUB format
- Markdown

### Additional Notification Channels

Extend `src/services/notification_service.py` to add:

- Slack notifications
- Discord webhooks
- SMS via Twilio

## 📈 Scaling Considerations

For production deployment:

1. **Use MongoDB Atlas** for managed database
2. **Add Redis/Celery** for async task queue
3. **Implement rate limiting** for LLM API calls
4. **Add retry logic** with exponential backoff
5. **Use environment-specific configs** (dev/staging/prod)
6. **Implement proper logging** (ELK stack, CloudWatch)
7. **Add monitoring** (Prometheus, Grafana)

## 🐛 Troubleshooting

**Issue: MongoDB connection fails**

- Check MongoDB is running: `mongod`
- Verify connection string in `.env`

**Issue: Gemini API errors**

- Verify API key is correct
- Check API quota/rate limits
- Review error logs in `logs/`

**Issue: Email notifications not working**

- Use app-specific password for Gmail
- Enable "Less secure app access" (or use OAuth2)
- Check SMTP settings in `.env`

**Issue: Chapters don't maintain context**

- Verify chapter summaries are being created
- Check `chapter_summaries` collection in MongoDB

## 📝 License

This project is for demonstration and evaluation purposes.

## 👤 Author

Created as part of the Book Generation System trial task.

## 🙏 Acknowledgments

- Google Gemini API for LLM capabilities
- MongoDB for flexible data storage
- Python ecosystem for robust libraries
