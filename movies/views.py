import httpx
from django.template.response import TemplateResponse
from django.core.paginator import Paginator, EmptyPage
import traceback
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from .models import Playlist, PlaylistItem, Movie
from asgiref.sync import sync_to_async
from django.views.decorators.clickjacking import xframe_options_exempt
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.http import HttpResponse
API_KEY = "569a626449cb32e3f1ff7230420b1dce"
BASE_URL = "https://api.themoviedb.org/3/movie/popular"
BASE_MOVIE_URL = "https://api.themoviedb.org/3/movie"
MAX_PAGES = 500

async def fetch_movies(page_number: int):
    url = f"{BASE_URL}?api_key={API_KEY}&language=ru-RU&page={page_number}"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        total_pages = min(MAX_PAGES, data.get("total_pages", 1))
        
        movies = [
            {
                "tmdb_id": movie.get("id"),
                "title": movie.get("title"),
                "release_date": movie.get("release_date"),
                "rating": movie.get("vote_average"),
                "stars": round((movie.get("vote_average") or 0) / 2),
                "poster_url": f"https://image.tmdb.org/t/p/w200{movie.get('poster_path')}" if movie.get("poster_path") else None,
                "overview": movie.get("overview"),
            }
            for movie in results
        ]

        return movies, total_pages

async def movies(request):
    try:
        page_number = int(request.GET.get("page", 1))
    except ValueError:
        page_number = 1

    await sync_to_async(lambda: request.session.update({"movies_page": page_number}))()
    await sync_to_async(request.session.save)()

    try:
        movies_list, total_pages = await fetch_movies(page_number)
        error_msg = "" if movies_list else "Фильмы не найдены или такой страницы не существует."
    except httpx.RequestError:
        movies_list = []
        total_pages = MAX_PAGES
        error_msg = "Ошибка при получении фильмов. Попробуйте позже."

    context = {
        "movies": movies_list,
        "page": page_number,
        "total_pages": total_pages,
        "prev_page": max(1, page_number - 1),
        "next_page": min(total_pages, page_number + 1),
        "error": error_msg,
    }

    return TemplateResponse(request, "movies/popular_movies.html", context)

async def movie_detail(request, tmdb_id):
    next_url = request.GET.get("next") or f"/movies/playlist/?page={page}"
    page = request.GET.get('page', 1)
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key
    
    try:
        playlist, _ = await sync_to_async(Playlist.objects.get_or_create)(session_key=session_key)
        in_playlist = await sync_to_async(lambda: playlist.items.filter(tmdb_id=tmdb_id).exists())()
        
        url = f"{BASE_MOVIE_URL}/{tmdb_id}?api_key={API_KEY}&language=ru-RU"
    
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json() if response.content else {}
            
            movie = {
                "tmdb_id": tmdb_id,
                "title": data.get("title") or "Нет названия",
                "original_title": data.get("original_title") or "",
                "release_date": data.get("release_date") or "-", 
                "rating": data.get("vote_average") or 0,
                "stars": round((data.get("vote_average") or 0) / 2),
                "poster_url": (f"https://image.tmdb.org/t/p/w300{data.get('poster_path')}" if data.get("poster_path") else "/static/movies/no-poster.jpg"),
                "backdrop_url": (
                f"https://image.tmdb.org/t/p/w780{data.get('backdrop_path')}"
                if data.get("backdrop_path") else "/static/movies/no-poster.jpg"
            ),
                "overview": data.get("overview") or "Описание отсутствует",
                "genres": [g["name"] for g in data.get("genres", [])] if data.get("genres") else [],
                "runtime": data.get("runtime") or "-",
            }

    except Exception :
        return redirect(next_url) 
    template = "movies/movie_detail.html"
    if request.headers.get("HX-Request"):
        template = "movies/partials/movie_detail_content.html"

    
    return TemplateResponse(
        request,
        template,
        {"movie": movie, "tmdb_id": tmdb_id, "in_playlist": in_playlist, "next_url": next_url}
    )
    
async def add_to_playlist(request, tmdb_id):
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key
    playlist, _ = await sync_to_async(Playlist.objects.get_or_create)(session_key=session_key)
    title = request.POST.get("title") or "Нет названия"
    poster_url = request.POST.get("poster_url") or "/static/movies/no-poster.jpg"
    await sync_to_async(PlaylistItem.objects.get_or_create)(
        playlist=playlist,
        tmdb_id=tmdb_id,
        defaults={"title": title, "poster_url": poster_url},
    )

    html = await sync_to_async(render_to_string)(
        "movies/_playlist_button.html",
        {
            "tmdb_id": tmdb_id,
            "in_playlist": True,
        },
        request=request,
    )
    return HttpResponse(html)

def playlist_view(request):
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key
    
    playlist, _ =  Playlist.objects.get_or_create(session_key=session_key)
    items = playlist.items.all()
    
    paginator = Paginator(items, 20) 
    try: 
        page = int(request.GET.get("page", 1))
    except (ValueError, TypeError):
        page = 1
    request.session["playlist_page"] = page    
    movies_page = request.session.get("movies_page", 1)     
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(1)
        page = 1 
    context = {
        "playlist": playlist,
        "items": page_obj.object_list,
        "page": page_obj.number,
        "total_pages": paginator.num_pages,
        "movies_page": movies_page,
    }   
        
    if request.headers.get("HX-Request"):
        return render(
            request,
            "movies/partials/playlist_content.html", context
        )
    return TemplateResponse(request, "movies/playlist.html", context)

@require_POST
def remove_from_playlist(request, item_id):
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    PlaylistItem.objects.filter(id=item_id, playlist__session_key=session_key).delete()

    playlist, _ = Playlist.objects.get_or_create(session_key=session_key)
    items = playlist.items.all().order_by("id")

    paginator = Paginator(items, 20)
    page_number = request.session.get("playlist_page", 1)
    try:
        page_obj = paginator.page(page_number)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
        page_number = page_obj.number
    movies_page = request.session.get("movies_page", 1)    
    context = {
        "playlist": playlist,
        "items": page_obj.object_list,
        "page": page_obj.number,
        "total_pages": paginator.num_pages,
        "movies_page": movies_page,
    }

    
    html = render_to_string("movies/partials/playlist_content.html", context, request=request)
    return HttpResponse(html)

    return render(request, "movies/playlist.html", context)


@xframe_options_exempt
def music_player(request):
    return render(request, "movies/player.html")

@xframe_options_exempt
def audio_player(request):
    return render(request, 'movies/audio_player.html')
