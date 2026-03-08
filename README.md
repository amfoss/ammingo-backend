# amMingo-backend
Backend for Open source alternative to Human Bingo 

## Deploying Manually

### First clone the repo to your local
```bash
git clone https://github.com/amfoss/ammingo-backend
cd ammingo-backend
```

### Setup virtual environment and install dependancies
```bash 
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run the app

```bash
fastapi dev app/main.py
```

## Deploy with docker 

### First clone the repo to your local
```bash
git clone https://github.com/amfoss/ammingo-backend
cd ammingo-backend
```

### Run the container
```bash
docker compose up -d
```


The app will be running on
`http://0.0.0.0:8000/`

You can find the docs at 
`http://0.0.0.0:8000/docs`