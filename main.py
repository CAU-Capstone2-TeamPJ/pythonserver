from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def hello():
    return {"message": "Server up!"}

@app.get("/healthz")
def healthz():
    return {"status": "ok"}
