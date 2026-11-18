# 🔭 Linkscope – AI-Powered Website Link Analysis

Linkscope is a web application that helps users understand a website better by simply entering its URL.

It analyzes the website and provides useful insights, including potential competitors, top 5 relevant search queries, SEO improvement suggestions, top 5 services offered, and the target audience.

The application is built using **FastAPI, SQLite, and a simple single-page frontend**. It uses the **Google Gemini API** to analyze website content and generate structured insights.

## Getting Started

Follow these steps to run the project locally.

### 1. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the example environment file:

```bash
cp .env.example .env
```

Add your Google Gemini API key and configure the model in the `.env` file.

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=your_model_name
```

### 4. Start the application

```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000
```

Once the server starts, you can access:

- **Application:** http://localhost:4000
- **API documentation:** http://localhost:4000/docs
- **Run tests:** `pytest`

### Running with Docker

You can also run the application using Docker:

```bash
docker build -t linkscope .
docker run -p 4000:4000 --env-file .env linkscope
```

### Deployment

Linkscope can be deployed on container hosting platforms such as Render, Railway, or Fly.io.

Configure the required environment variables on the hosting platform and mount a persistent volume at `/srv/data` to retain analysis history.

## API Endpoints

The main endpoint accepts a website URL and returns its analysis.

**POST `/link-analysis`**

Example request:

```json
{
  "url": "https://example.com",
  "force_refresh": false
}
```

Other available endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/history` | View previous analyses |
| GET | `/api/history/{id}` | Get a specific analysis |
| DELETE | `/api/history/{id}` | Delete an analysis |
| GET | `/health` | Check application status |

You can also test the main endpoint using cURL:

```bash
curl -X POST localhost:4000/link-analysis \
-H "Content-Type: application/json" \
-d '{"url":"https://example.com"}'
```

### Error Handling

The API returns errors in a consistent JSON format:

```json
{
  "success": false,
  "error": {
    "type": "error_type",
    "message": "Error description"
  }
}
```

It handles invalid or private URLs, unreachable websites, blocked requests, timeouts, and Gemini API failures using appropriate HTTP status codes (400, 422, 502, and 504).

## How the Application Works

The analysis process is divided into a few steps:

1. **URL Validation:** Checks whether the submitted URL is valid and safe to access.
2. **Website Extraction:** Fetches the homepage and, when available, up to two relevant pages such as About or Services. Unnecessary HTML content is removed.
3. **Website Analysis:** Sends the extracted website content to the Google Gemini API to generate insights across all five categories.
4. **Response Validation:** Uses Pydantic to validate the generated response. If the response doesn't match the expected structure, one correction attempt is made.
5. **AI Integration:** Uses Google Gemini API to process website content and generate structured analysis results.
6. **Database Storage:** Saves previous analyses in SQLite and uses caching to avoid repeating unnecessary requests.

## AI Integration – Google Gemini

Linkscope uses the **Google Gemini API** as its AI engine.

After extracting relevant information from a website, the application sends that content to Gemini for analysis. The generated results cover five areas:

- **Competitors:** Identifies potential competitors based on the website's content and business category.
- **Search Queries:** Suggests five relevant search queries that users might use to find the website's products or services.
- **SEO Suggestions:** Highlights possible SEO improvements to help improve website visibility.
- **Services:** Identifies up to five services offered by the website.
- **Target Audience:** Provides insights into the audience most likely to be interested in the website.

The response is validated using Pydantic to maintain a consistent output structure. If the generated response does not meet the expected format, the application makes one correction attempt.

### API Configuration

The Gemini API key is stored in environment variables instead of being hardcoded into the source code.

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=your_model_name
```

The model name should match the Gemini model configured in your application.

## Security Considerations

Security was considered throughout the development of Linkscope.

- Validates URLs before making requests.
- Checks every redirect to prevent access to private, loopback, and link-local IP addresses.
- Limits the amount of website content downloaded.
- Keeps API credentials in environment variables instead of hardcoding them.
- Excludes `.env` files from Git.

**Known limitation:** DNS rebinding is not completely prevented because of a possible race condition between IP validation and the actual connection. For production environments, pinning the resolved IP address or using an egress proxy would provide stronger protection.

## Keeping the Results Reliable

AI-generated results should not be treated as verified facts. To make this clear:

- Competitor suggestions and search queries are identified as AI-generated.
- Search volumes are not fabricated or presented as real statistics.
- Services are marked as either `website` (found on the website) or `inferred` (suggested by the AI).

## Performance and Cost Optimizations

A few optimizations have been included to keep the application efficient and reduce unnecessary Gemini API usage:

- Removes unnecessary HTML, repeated content, and website boilerplate before sending data for analysis.
- Limits the amount of extracted website content.
- Uses a single Gemini API request to generate all five analysis sections.
- Caches results for 24 hours using the website URL and content hash.
- Retries response correction only once when validation fails.

Token usage and response latency can be monitored through the API response metadata.

---

here is the Project URL : https://link-analysis-five.vercel.app/
