"""Sample jobs used when live APIs are unreachable. Fictional companies; links are placeholders."""
from __future__ import annotations

# (title, company, location, region, tags, salary)
_ROWS = [
    ("Python Backend Engineer", "Nimbus Labs", "Bengaluru, India", "india", ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"], "₹18–28 LPA"),
    ("Full Stack Developer (React + Node)", "Kiteworks India", "Pune, India", "india", ["React", "TypeScript", "Node.js", "MongoDB", "REST APIs"], "₹12–20 LPA"),
    ("Machine Learning Engineer", "Sutra AI", "Hyderabad, India", "india", ["Python", "PyTorch", "NLP", "Machine Learning", "AWS"], "₹22–35 LPA"),
    ("Data Analyst", "Bharat Retail Analytics", "Gurugram, India", "india", ["SQL", "Power BI", "Excel", "Python", "Data Analysis"], "₹7–12 LPA"),
    ("DevOps Engineer", "CloudKaveri", "Chennai, India", "india", ["Kubernetes", "Terraform", "AWS", "CI/CD", "Linux"], "₹15–25 LPA"),
    ("Frontend Engineer (React)", "Pixelwise", "Mumbai, India", "india", ["React", "TypeScript", "Tailwind CSS", "Redux", "Testing"], "₹10–18 LPA"),
    ("Generative AI Engineer", "Orbit Intelligence", "Bengaluru, India", "india", ["LLMs", "LangChain", "RAG", "Python", "FastAPI"], "₹25–40 LPA"),
    ("Software Engineer, Platform", "Nordlicht GmbH", "Berlin, Germany", "abroad", ["Java", "Spring Boot", "Kafka", "PostgreSQL", "Kubernetes"], "€65–85k"),
    ("Senior Python Developer", "Thames Digital", "London, United Kingdom", "abroad", ["Python", "Django", "PostgreSQL", "AWS", "Docker"], "£70–90k"),
    ("Data Scientist", "Maple Insights", "Toronto, Canada", "abroad", ["Python", "Pandas", "Scikit-learn", "SQL", "Machine Learning"], "CA$95–120k"),
    ("Full Stack Engineer", "Marina Pay", "Singapore", "abroad", ["React", "Node.js", "TypeScript", "PostgreSQL", "AWS"], "S$85–120k"),
    ("AI Engineer", "Dune Robotics", "Dubai, UAE", "abroad", ["Python", "Computer Vision", "PyTorch", "Docker", "Machine Learning"], "AED 18–28k/mo"),
    ("Backend Engineer (Go/Python)", "Canal Commerce", "Amsterdam, Netherlands", "abroad", ["Python", "Go", "Kafka", "Redis", "Microservices"], "€70–90k"),
    ("Remote Python Developer", "Distributed Co", "Remote (Worldwide)", "remote", ["Python", "FastAPI", "PostgreSQL", "Docker", "Git"], "$60–90k"),
    ("Remote React Developer", "Lumen Apps", "Remote (Worldwide)", "remote", ["React", "TypeScript", "Next.js", "Tailwind CSS", "GraphQL"], "$55–85k"),
    ("Remote LLM Application Engineer", "Quill Systems", "Remote (Asia-friendly)", "remote", ["LLMs", "LangChain", "LangGraph", "Python", "RAG"], "$70–110k"),
    ("Remote Data Engineer", "Streamline Data", "Remote (Worldwide)", "remote", ["Python", "Spark", "Airflow", "SQL", "AWS"], "$75–105k"),
    ("Remote QA Automation Engineer", "Bugless", "Remote (Worldwide)", "remote", ["Selenium", "Cypress", "Testing", "Python", "CI/CD"], "$40–60k"),
]


def mock_jobs() -> list[dict]:
    out = []
    for title, company, loc, region, tags, salary in _ROWS:
        slug = f"{company}-{title}".lower().replace(" ", "-").replace("(", "").replace(")", "").replace("/", "-").replace(",", "")
        out.append({
            "title": title, "company": company, "location": loc, "region": region, "tags": tags, "salary": salary,
            "url": f"https://example.com/jobs/{slug}", "apply_url": f"https://example.com/jobs/{slug}/apply",
            "description": f"{company} is hiring a {title}. You will design, build and ship features with {', '.join(tags)}. "
                           f"We value ownership, clear communication and measurable impact. Requirements: experience with {', '.join(tags[:4])}.",
            "source": "mock", "posted_at": "",
        })
    return out
