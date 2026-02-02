# AI-Powered Clothing Shop

A smarter approach to e-commerce search, deployed fully on Google Cloud Platform.

🔗 **Live Demo:** [https://tailor-shop-682769211091.us-east1.run.app](https://tailor-shop-682769211091.us-east1.run.app)

## 💡 The Idea: Why "Smart Categorization"?

Standard e-commerce search engines (like those used by major retailers such as Zara or Reserved) often fail at understanding specific semantic negation or complex attribute combinations. 

**The Problem:**
If you search for *"coat without buttons"* (`płaszcz bez guzików`) on many platforms, you often get incorrect results—simply returning *all* coats, most of which have buttons. The search engine matches keywords but fails to understand the structural requirement of "without".

**My Solution: Structured Intelligence**
Instead of relying solely on vector embeddings (which can be "fuzzy" and prone to hallucinations) or simple keyword matching, this project uses a **Deterministic AI Categorization** approach driven by Google's Gemini models via Vertex AI.

### How it Works

1.  **Ingestion Phase (Data Enrichment):**
    *   Every product category (e.g., Coats, Pants) has a rigid schema of constant features (e.g., `has_buttons`, `style`, `material`).
    *   The system supports an extensive range of features per category; when these are properly adjusted and fine-tuned, the potential for extremely high-quality and relevant search results is significant.
    *   When a product is uploaded, Gemini analyzes its images and description to deterministically assign values to these specific features.

2.  **Search Phase:**
    *   **Category Detection:** When a user searches, Gemini first decides the target category (or uses the current context).
    *   **Feature Extraction:** Gemini maps the user's natural language prompt to the strict schema of that category.
    *   **Example:** A search for *"dark coat with belt"* translates to:
        *   **Category:** Coat
        *   **Features:** `darkness="dark"`, `has_belt=True`
    *   **Execution:** The backend runs a precise database filter based on these structured values.

3.  **Visual Search (Image-to-Product):**
    *   **Person Detection:** When a user uploads an image, Gemini first detects people within the frame. The user can then select the specific person they want to analyze to ensure focus and precision.
    *   **Category & Feature Identification:** Once a person is selected, the system identifies clothing categories that exist in the shop's catalog.
    *   **Mapping:** Finally, Gemini extracts visual features from the selected items to match them against the structured data in the database, finding the closest physical matches.

This methodology uses **few-shot prompting** to ensure high precision. The result is a search experience that is strictly predictive: it eliminates "stupid errors."

### Handling Edge Cases
Because this system is strict, it can sometimes be too rigid. To solve this, if Gemini cannot fully map a prompt to existing inventory features, it generates **Smart Suggestions**—proposing alternative, valid queries to guide the user toward available products.

All prompts and AI decisions are cached in **Redis** and logged in **PostgreSQL** for speed and future analysis.

## 🏗️ Architecture

The application is built entirely on **Google Cloud Platform (GCP)**, designed for scalability and performance.

*   **Compute:** 
    *   **Google Cloud Run:** Hosts the Django application container (Serverless).
*   **Data & State:**
    *   **Google Compute Engine (VM):** Hosts the self-managed **PostgreSQL** database and **Redis** instance (used for caching AI responses).
*   **AI & ML:**
    *   **Vertex AI:** Integrates Gemini for text analysis and image recognition.
*   **Storage:**
    *   **Google Cloud Storage:** Stores static assets and product media.

## 📊 Data Sourcing (Web Scraping)

The catalog for this project was built by sourcing real-world data from existing retailers. To achieve this, I developed a custom web scraping solution specifically for Reserved.com.

You can find the details and the code for the scraping process in this repository:
👉 [Web Scraping Reserved.com](https://github.com/JakubRybak/web_scraping_reserved_com)

## 🛠️ Technology Stack

*   **Backend:** Python, Django
*   **Frontend:** HTMX, Django Templates, CSS
*   **Database:** PostgreSQL
*   **Caching:** Redis
*   **AI:** Google Vertex AI (Gemini)
*   **Infrastructure:** Docker, Google Cloud Run, Google Compute Engine

## 🔮 Future Roadmap

*   **Hybrid Search:** Investigating the integration of vector embeddings *alongside* the current strict filtering. This would allow for a "best of both worlds" approach—maintaining the precision of structured data while adding the flexibility of semantic similarity for more abstract queries.