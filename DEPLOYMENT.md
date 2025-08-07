# 🚀 Deployment Guide

## Option 1: Local Server (Quick Start)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set API Key
```bash
export GROQ_API_KEY="your-groq-api-key-here"
```

### 3. Run the Server
```bash
python api.py
```

### 4. Access the Web Interface
Open your browser to: `http://localhost:8000`

## Option 2: Cloud Deployment (Recommended)

### A. Railway (Easiest)
1. Go to [railway.app](https://railway.app)
2. Connect your GitHub repo
3. Add environment variable: `GROQ_API_KEY=your-key`
4. Deploy automatically

### B. Heroku
1. Create `Procfile`:
```
web: uvicorn api:app --host 0.0.0.0 --port $PORT
```

2. Deploy:
```bash
heroku create your-app-name
heroku config:set GROQ_API_KEY=your-key
git push heroku main
```

### C. DigitalOcean App Platform
1. Connect your GitHub repo
2. Set environment variable: `GROQ_API_KEY`
3. Deploy

### D. AWS/GCP/Azure
Use their container services or serverless functions.

## Option 3: Docker Deployment

### 1. Create Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Build and Run
```bash
docker build -t yacht-seo .
docker run -p 8000:8000 -e GROQ_API_KEY=your-key yacht-seo
```

## Option 4: VPS/Server

### 1. SSH into your server
```bash
ssh user@your-server.com
```

### 2. Clone and setup
```bash
git clone https://github.com/your-username/Yacht-SEO.git
cd Yacht-SEO
pip install -r requirements.txt
export GROQ_API_KEY="your-key"
```

### 3. Run with systemd (for persistence)
Create `/etc/systemd/system/yacht-seo.service`:
```ini
[Unit]
Description=Yacht SEO Generator
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/Yacht-SEO
Environment=GROQ_API_KEY=your-key
ExecStart=/usr/bin/python3 api.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### 4. Start the service
```bash
sudo systemctl enable yacht-seo
sudo systemctl start yacht-seo
```

## Option 5: Reverse Proxy with Nginx

### 1. Install Nginx
```bash
sudo apt update
sudo apt install nginx
```

### 2. Configure Nginx
Create `/etc/nginx/sites-available/yacht-seo`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Enable the site
```bash
sudo ln -s /etc/nginx/sites-available/yacht-seo /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Security Considerations

### 1. Environment Variables
- Never commit API keys to git
- Use environment variables or secrets management
- Rotate keys regularly

### 2. Rate Limiting
Add rate limiting to prevent abuse:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/generate")
@limiter.limit("10/minute")
async def generate_from_csv(request: Request, file: UploadFile = File(...)):
    # ... existing code
```

### 3. Authentication (Optional)
Add basic auth for private use:
```python
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import Depends, HTTPException, status

security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != "admin" or credentials.password != "password":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@app.post("/generate")
async def generate_from_csv(
    username: str = Depends(verify_credentials),
    file: UploadFile = File(...)
):
    # ... existing code
```

## Usage Examples

### Web Interface
1. Open `http://your-domain.com`
2. Upload CSV file
3. Click "Generate Descriptions"
4. Download results

### API Usage
```bash
# Upload CSV file
curl -X POST "http://your-domain.com/generate" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@yachts.csv"

# Generate single yacht
curl -X POST "http://your-domain.com/generate-single" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "GENNY",
    "length": 23.87,
    "year": 2021,
    "price": "€58,000 – €70,000",
    "cabins": 5,
    "guests": 10,
    "crew": 6,
    "watertoys": "Jacuzzi; Jet-ski; Seabob; SUP",
    "location": "Greece",
    "model": "Sunreef 80",
    "builder": "Sunreef Yachts"
  }'
```

## Monitoring

### Health Check
```bash
curl http://your-domain.com/health
```

### Logs
```bash
# If using systemd
sudo journalctl -u yacht-seo -f

# If using Docker
docker logs -f container-name
```

## Cost Optimization

- Use appropriate instance sizes
- Consider serverless for low usage
- Monitor API usage and costs
- Set up alerts for high usage
