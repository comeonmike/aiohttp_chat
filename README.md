## Simple aiohttp chat (slack)
#### Made fo myself
### Preparation:
```
pip install -r requirements.txt
cd aiochat/
python migrate.py
redis-server
```
### Run:
```
python app.py
```
or
```
gunicorn wsgi:app --bind localhost:8080 --worker-class aiohttp.GunicornWebWorker
```

### Based on  [this repository](https://github.com/samael500/aiochat) (MIT license)

### Fixes:
- fixed work with websockets
- fixed launch with wsgi
- the code began to work with support for all the latest versions of python modules and python3.8
