from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Body, status, Response, Query
import pydantic
import httpx
import json
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # your frontend
    allow_credentials=True,
    allow_methods=["*"],  # or ["POST", "GET"] if you want to restrict
    allow_headers=["*"],
)

OMDB_API_KEY = "b36a556f"
MOVIES_FILE = "movies.json"

def load_movies():
    if not os.path.exists(MOVIES_FILE):
        return []

    try:
        with open(MOVIES_FILE, "r") as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except json.JSONDecodeError:
        return []  # file exists but contains invalid JSON

def save_movie_if_not_exists(new_movie):
    movies = load_movies()

    imdb_ids = {movie["imdbID"] for movie in movies}

    if new_movie["imdbID"] in imdb_ids:
        return False  # already exists

    movies.append(new_movie)
    with open(MOVIES_FILE, "w") as f:
        json.dump(movies, f, indent=2)

    return True

async def fetch_movie_job(imdb_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get("http://www.omdbapi.com/", params={
            "apikey": OMDB_API_KEY,
            "i": imdb_id
        })
        data = response.json()
        return data if data.get("Response") == "True" else None



@app.get("/movie")
async def fetch_movie(i: str = Query("")):
    url = "http://www.omdbapi.com/"
    params = {
        "apikey": OMDB_API_KEY,
        "i": i  # 's' = search (returns up to 10 results)
    }
    data = await fetch_movie_job(i)
    return data  # returns list of movies



@app.get("/search-movie")
async def search_movie(title: str = Query(..., description="Movie title to search")):
    url = "http://www.omdbapi.com/"
    params = {
        "apikey": OMDB_API_KEY,
        "t": title  # you can also use "s" for search by name
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        data = response.json()

    return data

@app.get("/external-movies")
async def fetch_external_movies(query: str = Query("Batman")):
    url = "http://www.omdbapi.com/"
    params = {
        "apikey": OMDB_API_KEY,
        "s": query,
        "plot": 'full'
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        data = response.json()

    return data.get("Search", [])

class IMDbRequest(pydantic.BaseModel):
    i: str

@app.post("/save", status_code=status.HTTP_201_CREATED)
async def save_movie_to_file(response: Response, body: IMDbRequest = Body(...)):
    movie = await fetch_movie_job(body.i)

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    was_added = save_movie_if_not_exists(movie)

    if not was_added:
        response.status_code = status.HTTP_200_OK

    return {
        "message": "Movie added" if was_added else "Movie already exists",
        "movie": movie
    }
