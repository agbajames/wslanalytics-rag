# WSL Analytics RAG

Actively developing and extending this project

A Retrieval-Augmented Generation (RAG) system that generates data-driven Women's Super League match recaps and previews using FastAPI, Supabase, and OpenAI.

## Overview

This project demonstrates a RAG implementation that combines historical match data, team statistics, and large language models to produce accurate, factual sports content. By grounding AI-generated text in real data retrieved from a PostgreSQL database, the system aims to prevent hallucinations and ensure all match information is verifiable.

**Current Status**: Core functionality is working, but actively adding features, refining prompts, and improving data retrieval logic.

### Features

- ✅ **RAG Architecture**: Retrieves relevant historical data before generation to ensure factual accuracy
- ✅ **FastAPI Backend**: Async Python API with automatic OpenAPI documentation
- ✅ **Supabase Integration**: PostgreSQL database with connection pooling for efficient data access
- ✅ **OpenAI Integration**: Uses GPT models for natural language generation grounded in retrieved data
- ✅ **Match Recaps**: Generates post-match analysis based on actual match statistics and results
- ✅ **Match Previews**: Creates pre-match content using historical head-to-head data and team form
- 🔄 **Prompt Optimization**: Iterating on prompts to improve content quality and style
- 🔄 **Data Pipeline**: Refining SQL queries and data retrieval logic
- 📋 **Planned**: User authentication, caching layer, multiple output formats

## Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTP Request (team names, match info)
       ↓
┌─────────────────────────────────────────┐
│           FastAPI Application            │
│  ┌─────────────────────────────────┐   │
│  │     RAG Pipeline                 │   │
│  │  1. Parse request parameters     │   │
│  │  2. Retrieve relevant data       │   │
│  │  3. Format context for LLM       │   │
│  │  4. Generate with grounded data  │   │
│  └─────────────────────────────────┘   │
└──────┬──────────────────────┬──────────┘
       │                       │
       ↓                       ↓
┌──────────────┐      ┌──────────────┐
│   Supabase   │      │   OpenAI     │
│  PostgreSQL  │      │   GPT API    │
│              │      │              │
│ • Matches    │      │ • Recaps     │
│ • Teams      │      │ • Previews   │
│ • Stats      │      │ • Analysis   │
└──────────────┘      └──────────────┘
```

## Tech Stack

- **Python 3.11+**: Modern async/await patterns
- **FastAPI**: High-performance async web framework
- **asyncpg**: PostgreSQL database driver with connection pooling
- **Supabase**: Managed PostgreSQL with built-in authentication
- **OpenAI Python SDK**: Integration with GPT models
- **Pydantic**: Data validation and settings management
- **uvicorn**: ASGI server for production deployment

## Project Structure

```
wslanalytics-rag/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── deps.py              # Database connection pooling
│   ├── guards.py            # Request validation and sanitization
│   ├── llm.py               # OpenAI integration and prompt templates
│   ├── render.py            # Content generation orchestration
│   ├── settings.py          # Configuration management
│   └── schemas.py           # Pydantic models for requests/responses
├── prompts/                 # LLM prompt templates
├── sql/                     # Database queries
├── templates/               # Jinja2 templates for content formatting
├── tools/                   # Utility scripts
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
├── .gitignore
└── README.md
```

## Installation

### Prerequisites

- Python 3.11 or higher
- Supabase account with a project
- OpenAI API key
- Git

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/wslanalytics-rag.git
   cd wslanalytics-rag
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your credentials:
   ```env
   # Supabase Configuration
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-supabase-anon-key
   DATABASE_URL=postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres
   
   # OpenAI Configuration
   OPENAI_API_KEY=your-openai-api-key
   OPENAI_MODEL=gpt-4-turbo-preview
   
   # Application Settings
   ENVIRONMENT=development
   DEBUG=true
   ```

5. **Initialize database schema** (if needed)
   ```bash
   # Your database should have tables for:
   # - matches (match results and statistics)
   # - teams (team information and ratings)
   # - players (player statistics)
   ```

## Usage

### Starting the Server

**Development mode:**
```bash
uvicorn app.main:app --reload --port 8000
```

**Production mode:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### API Endpoints

#### Generate Match Recap

Generate a post-match recap based on actual match data.

```bash
POST /api/recap
Content-Type: application/json

{
  "home_team": "Chelsea Women",
  "away_team": "Arsenal Women",
  "match_date": "2024-03-15",
  "round": 20
}
```

**Response:**
```json
{
  "content": "# Chelsea Women 2-1 Arsenal Women\n\nIn a thrilling top-of-the-table clash...",
  "metadata": {
    "home_team": "Chelsea Women",
    "away_team": "Arsenal Women",
    "score": "2-1",
    "venue": "Stamford Bridge",
    "attendance": 38641,
    "date": "2024-03-15"
  },
  "statistics": {
    "possession": {"home": 52, "away": 48},
    "shots": {"home": 14, "away": 11},
    "shots_on_target": {"home": 6, "away": 4}
  }
}
```

#### Generate Match Preview

Generate a pre-match preview using historical head-to-head data.

```bash
POST /api/preview
Content-Type: application/json

{
  "home_team": "Manchester United Women",
  "away_team": "Manchester City Women",
  "match_date": "2024-03-22",
  "round": 21
}
```

**Response:**
```json
{
  "content": "# Manchester Derby Preview\n\nThe Manchester rivals meet again...",
  "metadata": {
    "home_team": "Manchester United Women",
    "away_team": "Manchester City Women",
    "kickoff": "2024-03-22T19:00:00Z",
    "venue": "Leigh Sports Village"
  },
  "context": {
    "head_to_head": {
      "total_matches": 15,
      "home_wins": 3,
      "away_wins": 9,
      "draws": 3
    },
    "form": {
      "home": "W-W-D-L-W",
      "away": "W-W-W-W-D"
    }
  }
}
```

### Interactive API Documentation

FastAPI provides automatic interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## How It Works: The RAG Pipeline

### 1. Request Processing
When a recap or preview request comes in, the system validates the input parameters (team names, dates) and sanitizes them to prevent SQL injection.

### 2. Data Retrieval
The system queries the Supabase database to retrieve relevant information:
- For recaps: Match result, statistics, player performances, possession, shots, cards
- For previews: Head-to-head history, recent form, team ratings, injury reports

### 3. Context Formation
Retrieved data is formatted into a structured context that provides the LLM with factual information:

```python
context = {
    "match": {
        "home_team": "Chelsea Women",
        "away_team": "Arsenal Women",
        "score": "2-1",
        "date": "2024-03-15",
        "venue": "Stamford Bridge"
    },
    "statistics": {...},
    "goals": [...],
    "cards": [...]
}
```

### 4. Prompt Engineering
A carefully crafted prompt combines:
- The retrieved context (facts)
- The generation task (recap or preview)
- Style guidelines (professional sports journalism)
- Constraints (only use provided data)

### 5. LLM Generation
The OpenAI API generates natural language content using the provided context. The LLM is instructed to:
- Only reference facts from the retrieved data
- Maintain a professional, analytical tone
- Include specific statistics and details
- Avoid speculation or fabrication

### 6. Response Formatting
The generated content is formatted, metadata is attached, and the complete response is returned to the client.

## Preventing Hallucinations

The RAG approach prevents common LLM issues:

1. **Grounded Generation**: All facts come from the database, not the model's training data
2. **Explicit Context**: The prompt explicitly provides the data to reference
3. **Constrained Output**: Instructions tell the model to only use provided information
4. **Verification**: Statistics and facts can be traced back to database records

## Database Schema

### Core Tables

**matches**
- `id`: Primary key
- `home_team_id`, `away_team_id`: Foreign keys to teams
- `home_score`, `away_score`: Match result
- `match_date`: Date of the match
- `round`: League round number
- `venue`: Stadium name
- `attendance`: Crowd size

**teams**
- `id`: Primary key
- `name`: Team name
- `rating`: Current ELO or power rating
- `wins`, `draws`, `losses`: Season record

**match_statistics**
- `match_id`: Foreign key
- `team_id`: Foreign key
- `possession`: Possession percentage
- `shots`, `shots_on_target`: Shot statistics
- `corners`, `fouls`: Match events

## Development Status & Roadmap

This is an active project that I'm continuously improving. Here's what I'm working on:

### ✅ Completed
- Core RAG pipeline implementation
- FastAPI endpoints for recaps and previews
- Database connection pooling with asyncpg
- Basic prompt templates
- OpenAI API integration

### 🔄 In Progress
- Refining prompt engineering for better content quality
- Optimizing database queries for faster retrieval
- Adding more comprehensive match statistics
- Improving error handling and validation
- Testing different LLM models and parameters

### 📋 Planned Features
- Redis caching layer for frequently accessed data
- User authentication and API keys
- Web frontend for content generation
- Batch processing for multiple matches
- Different content formats (social media posts, newsletters)
- Enhanced analytics and insights
- Docker containerization
- CI/CD pipeline

### 🐛 Known Issues
- SSL context in `deps.py` is insecure (development only)
- Rate limiting not yet implemented


## Contact

James Agba - [GitHub](https://github.com/agbajames

Project Link: [https://github.com/yourusername/wslanalytics-rag](https://github.com/yourusername/wslanalytics-rag)

---

**Built with ❤️ for Women's Football Analytics**