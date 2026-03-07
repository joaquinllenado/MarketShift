from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prefect import flow, task

app = FastAPI(title="MarketShift API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@task
def build_greeting() -> str:
    return "Hello World from Prefect!"


@flow(name="hello-world-flow")
def hello_flow() -> str:
    greeting = build_greeting()
    return greeting


@app.get("/hello")
def hello():
    result = hello_flow()
    return {"message": result}
